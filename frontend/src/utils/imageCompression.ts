export interface CompressionOptions {
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
}

/**
 * Compresses an image file using native HTML5 Canvas.
 * Downscales dimensions if they exceed maxWidth or maxHeight while preserving aspect ratio,
 * and encodes to image/jpeg with the specified quality.
 * Falls back to the original file if canvas is unsupported (e.g. non-browser/test env)
 * or if compression fails.
 */
export async function compressImage(
  file: File,
  options: CompressionOptions = {}
): Promise<File> {
  const { maxWidth = 1920, maxHeight = 1080, quality = 0.8 } = options;

  // If not an image, return original file
  if (!file.type || !file.type.startsWith('image/')) {
    return file;
  }

  // Check if we are in an environment with DOM & canvas support
  if (typeof document === 'undefined' || typeof window === 'undefined') {
    return file;
  }

  return new Promise((resolve) => {
    if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') {
      resolve(file);
      return;
    }

    let objectUrl = '';
    try {
      objectUrl = URL.createObjectURL(file);
    } catch {
      resolve(file);
      return;
    }

    const img = new Image();

    img.onload = () => {
      try {
        URL.revokeObjectURL(objectUrl);
        let { width, height } = img;

        if (width <= 0 || height <= 0) {
          resolve(file);
          return;
        }

        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        if (!ctx || typeof canvas.toBlob !== 'function') {
          resolve(file);
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(file);
              return;
            }
            const cleanName = file.name.replace(/\.[^/.]+$/, '');
            const compressedFile = new File([blob], `${cleanName}.jpg`, {
              type: 'image/jpeg',
              lastModified: Date.now(),
            });
            resolve(compressedFile);
          },
          'image/jpeg',
          quality
        );
      } catch {
        resolve(file);
      }
    };

    img.onerror = () => {
      try {
        URL.revokeObjectURL(objectUrl);
      } catch {
        // ignore
      }
      resolve(file);
    };

    img.src = objectUrl;
  });
}
