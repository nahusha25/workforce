import type { Activity, CatalogueMaterial, MaterialTransaction } from '../api/dailyWork';

export const DISTANCE_UOMS = new Set([
  'm',
  'metre',
  'metres',
  'meter',
  'meters',
  'mtr',
  'mtrs',
]);

/**
 * Check if a unit of measure represents length / distance.
 */
export const isDistanceUom = (uom?: string | null): boolean => {
  if (!uom) return false;
  return DISTANCE_UOMS.has(uom.trim().toLowerCase());
};

/**
 * Check if two units of measure are compatible for synchronization.
 */
export const areUomsCompatible = (
  uom1?: string | null,
  uom2?: string | null
): boolean => {
  if (!uom1 || !uom2) return false;
  const s1 = uom1.trim().toLowerCase();
  const s2 = uom2.trim().toLowerCase();
  if (s1 === s2) return true;
  if (isDistanceUom(s1) && isDistanceUom(s2)) return true;
  return false;
};

/**
 * Format and standardize the unit of measure for display across the measurement table,
 * total summary, badges, and validation/help texts.
 * - Distance units ('metre', 'metres', 'm', 'mtr', etc.) are standardized consistently to 'metres'.
 * - Non-distance units (such as 'pcs', 'nos', etc.) are preserved cleanly.
 * - Defaults to 'metres' when not specified.
 */
export const getActivityUnitDisplay = (actOrUom?: Activity | string | null): string => {
  if (!actOrUom) return 'metres';
  const uom = typeof actOrUom === 'string' ? actOrUom : actOrUom.unit_of_measure;
  if (!uom || !uom.trim()) return 'metres';
  const clean = uom.trim();
  if (isDistanceUom(clean)) {
    return 'metres';
  }
  return clean.toLowerCase();
};

export interface MaterialMappingResult {
  material: CatalogueMaterial | null;
  reason?: string;
  isMapped: boolean;
}

/**
 * Find the catalogue inventory material that reliably maps to the given activity.
 * Returns an explanatory reason when no reliable mapping exists instead of guessing.
 */
export const findMatchingCatalogueMaterial = (
  activity?: Activity | null,
  catalogueMaterials: CatalogueMaterial[] = []
): MaterialMappingResult => {
  if (!activity) {
    return {
      material: null,
      reason: 'No activity selected.',
      isMapped: false,
    };
  }

  const activeMaterials = catalogueMaterials.filter((m) => m.is_active);
  const isDistanceAct =
    isDistanceUom(activity.unit_of_measure) ||
    activity.category.toLowerCase() === 'cable';

  // 1. Filter by category
  const categoryMatches = activeMaterials.filter(
    (m) => m.category.toLowerCase() === activity.category.toLowerCase()
  );

  if (categoryMatches.length === 0) {
    return {
      material: null,
      reason: `No active catalogue material found for activity category "${activity.category}".`,
      isMapped: false,
    };
  }

  // 2. Filter by compatible unit of measure (e.g. metre to metre, not metre to box)
  const compatibleMatches = categoryMatches.filter((m) => {
    if (isDistanceAct) {
      return isDistanceUom(m.unit_of_measure);
    }
    return areUomsCompatible(m.unit_of_measure, activity.unit_of_measure);
  });

  if (compatibleMatches.length === 0) {
    return {
      material: null,
      reason: `No catalogue material found with category "${activity.category}" and compatible unit of measure ("${activity.unit_of_measure}").`,
      isMapped: false,
    };
  }

  // 3. Exactly one compatible match
  if (compatibleMatches.length === 1) {
    return {
      material: compatibleMatches[0],
      isMapped: true,
    };
  }

  // 4. Exact name match disambiguation
  const nameMatch = compatibleMatches.find(
    (m) => m.name.trim().toLowerCase() === activity.name.trim().toLowerCase()
  );
  if (nameMatch) {
    return {
      material: nameMatch,
      isMapped: true,
    };
  }

  // 5. Category cable keyword disambiguation
  if (activity.category.toLowerCase() === 'cable') {
    const cableMatches = compatibleMatches.filter((m) =>
      m.name.toLowerCase().includes('cable')
    );
    if (cableMatches.length === 1) {
      return {
        material: cableMatches[0],
        isMapped: true,
      };
    }
  }

  return {
    material: null,
    reason: `Multiple catalogue materials match category "${activity.category}" and unit "${activity.unit_of_measure}". Please select the specific material in Attachments & Materials.`,
    isMapped: false,
  };
};

/**
 * Determine if an existing MaterialTransaction is the matching consumed-material
 * transaction that should be synchronized with the activity's measurements.
 *
 * Enforces:
 * - Must be transaction_type === 'consumed' (never 'purchased').
 * - Unrelated materials (e.g. consumables, tools, incompatible units like boxes) return false.
 * - Resilient to (activity, tx) or (tx, activity) argument ordering.
 */
export const isMatchingConsumedMaterial = (
  param1?: Activity | MaterialTransaction | null,
  param2?: Activity | MaterialTransaction | null,
  catalogueMaterials: CatalogueMaterial[] = []
): boolean => {
  if (!param1 || !param2) return false;

  let activity: Activity;
  let tx: MaterialTransaction;

  if ('transaction_type' in param1) {
    tx = param1 as MaterialTransaction;
    activity = param2 as Activity;
  } else if ('transaction_type' in param2) {
    activity = param1 as Activity;
    tx = param2 as MaterialTransaction;
  } else {
    return false;
  }

  if (tx.transaction_type !== 'consumed') return false;

  const isDistanceAct =
    isDistanceUom(activity.unit_of_measure) ||
    activity.category.toLowerCase() === 'cable';

  // If transaction has material_id, verify against catalogue material
  if (tx.material_id) {
    const mat = catalogueMaterials.find((m) => m.id === tx.material_id);
    if (mat) {
      if (mat.category.toLowerCase() !== activity.category.toLowerCase()) {
        return false;
      }
      if (isDistanceAct) {
        return isDistanceUom(mat.unit_of_measure);
      }
      return areUomsCompatible(mat.unit_of_measure, activity.unit_of_measure);
    }
  }

  // Direct item_name comparison
  const txName = (tx.item_name || '').trim().toLowerCase();
  const actName = (activity.name || '').trim().toLowerCase();
  if (txName === actName) return true;
  if (activity.category.toLowerCase() === 'cable' && txName.includes('cable')) {
    return true;
  }

  return false;
};
