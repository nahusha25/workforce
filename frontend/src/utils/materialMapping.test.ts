import { describe, it, expect } from 'vitest';
import {
  isDistanceUom,
  areUomsCompatible,
  findMatchingCatalogueMaterial,
  isMatchingConsumedMaterial,
  getActivityUnitDisplay,
} from './materialMapping';
import type { Activity, CatalogueMaterial, MaterialTransaction } from '../api/dailyWork';

describe('materialMapping utility', () => {
  describe('isDistanceUom', () => {
    it('recognizes standard distance / length units', () => {
      expect(isDistanceUom('m')).toBe(true);
      expect(isDistanceUom('metre')).toBe(true);
      expect(isDistanceUom('metres')).toBe(true);
      expect(isDistanceUom('meter')).toBe(true);
      expect(isDistanceUom('meters')).toBe(true);
      expect(isDistanceUom('mtr')).toBe(true);
      expect(isDistanceUom('mtrs')).toBe(true);
      expect(isDistanceUom(' MTR ')).toBe(true);
    });

    it('rejects non-distance units and empty values', () => {
      expect(isDistanceUom('pcs')).toBe(false);
      expect(isDistanceUom('box')).toBe(false);
      expect(isDistanceUom('kg')).toBe(false);
      expect(isDistanceUom(null)).toBe(false);
      expect(isDistanceUom(undefined)).toBe(false);
      expect(isDistanceUom('')).toBe(false);
    });
  });

  describe('getActivityUnitDisplay', () => {
    it('standardizes distance units consistently to metres', () => {
      expect(getActivityUnitDisplay('metre')).toBe('metres');
      expect(getActivityUnitDisplay('metres')).toBe('metres');
      expect(getActivityUnitDisplay('m')).toBe('metres');
      expect(getActivityUnitDisplay('mtr')).toBe('metres');
      expect(getActivityUnitDisplay(' MTR ')).toBe('metres');
      expect(getActivityUnitDisplay('meter')).toBe('metres');
      expect(getActivityUnitDisplay('meters')).toBe('metres');
    });

    it('preserves pcs and other non-distance units', () => {
      expect(getActivityUnitDisplay('pcs')).toBe('pcs');
      expect(getActivityUnitDisplay('PCS')).toBe('pcs');
      expect(getActivityUnitDisplay('nos')).toBe('nos');
    });

    it('accepts Activity objects directly', () => {
      expect(getActivityUnitDisplay({ unit_of_measure: 'pcs' } as Activity)).toBe('pcs');
      expect(getActivityUnitDisplay({ unit_of_measure: 'metre' } as Activity)).toBe('metres');
      expect(getActivityUnitDisplay({ unit_of_measure: 'metres' } as Activity)).toBe('metres');
    });

    it('falls back to metres when missing or empty', () => {
      expect(getActivityUnitDisplay(null)).toBe('metres');
      expect(getActivityUnitDisplay(undefined)).toBe('metres');
      expect(getActivityUnitDisplay('')).toBe('metres');
    });
  });

  describe('areUomsCompatible', () => {
    it('considers identical units compatible', () => {
      expect(areUomsCompatible('pcs', 'pcs')).toBe(true);
      expect(areUomsCompatible('BOX', 'box')).toBe(true);
    });

    it('considers distance units mutually compatible', () => {
      expect(areUomsCompatible('metre', 'mtr')).toBe(true);
      expect(areUomsCompatible('metres', 'm')).toBe(true);
    });

    it('rejects incompatible units or missing values', () => {
      expect(areUomsCompatible('metres', 'pcs')).toBe(false);
      expect(areUomsCompatible('mtr', 'box')).toBe(false);
      expect(areUomsCompatible(null, 'mtr')).toBe(false);
      expect(areUomsCompatible('mtr', undefined)).toBe(false);
    });
  });

  describe('findMatchingCatalogueMaterial', () => {
    const cableActivity: Activity = {
      id: 'act-cabling',
      name: 'Cable Pulling',
      category: 'cable',
      unit_of_measure: 'metres',
      approved_rate: 10,
      is_active: true,
    };

    const mockCatalogue: CatalogueMaterial[] = [
      {
        id: 'mat-1',
        name: 'Cat6 Cable 30m',
        category: 'cable',
        unit_of_measure: 'mtr',
        purchase_approval_limit: 1000,
        is_active: true,
      },
      {
        id: 'mat-2',
        name: 'RJ45 Connectors',
        category: 'accessories',
        unit_of_measure: 'pcs',
        purchase_approval_limit: 500,
        is_active: true,
      },
    ];

    it('returns matched catalogue material when category and unit match', () => {
      const result = findMatchingCatalogueMaterial(cableActivity, mockCatalogue);
      expect(result.isMapped).toBe(true);
      expect(result.material?.id).toBe('mat-1');
    });

    it('returns explanation reason when activity is null', () => {
      const result = findMatchingCatalogueMaterial(null, mockCatalogue);
      expect(result.isMapped).toBe(false);
      expect(result.material).toBeNull();
      expect(result.reason).toContain('No activity selected');
    });

    it('returns explanation reason when no catalogue materials match category', () => {
      const deviceActivity: Activity = {
        id: 'act-dev',
        name: 'Camera Mounting',
        category: 'device',
        unit_of_measure: 'pcs',
        approved_rate: 50,
        is_active: true,
      };

      const result = findMatchingCatalogueMaterial(deviceActivity, mockCatalogue);
      expect(result.isMapped).toBe(false);
      expect(result.material).toBeNull();
      expect(result.reason).toContain('No active catalogue material found for activity category "device"');
    });

    it('returns explanation reason when catalogue matches category but not unit of measure', () => {
      const incompatibleCat = [
        {
          id: 'mat-cable-box',
          name: 'Cable Drum (Box)',
          category: 'cable',
          unit_of_measure: 'box',
          purchase_approval_limit: 5000,
          is_active: true,
        },
      ];

      const result = findMatchingCatalogueMaterial(cableActivity, incompatibleCat);
      expect(result.isMapped).toBe(false);
      expect(result.material).toBeNull();
      expect(result.reason).toContain('compatible unit of measure');
    });

    it('disambiguates between multiple materials by name or cable keyword', () => {
      const multiCables: CatalogueMaterial[] = [
        {
          id: 'mat-c1',
          name: 'Cat6 Cable',
          category: 'cable',
          unit_of_measure: 'mtr',
          purchase_approval_limit: 1000,
          is_active: true,
        },
        {
          id: 'mat-c2',
          name: 'Armored Cable',
          category: 'cable',
          unit_of_measure: 'mtr',
          purchase_approval_limit: 2000,
          is_active: true,
        },
      ];

      // Exact name match
      const exactAct: Activity = {
        ...cableActivity,
        name: 'Cat6 Cable',
      };
      const resExact = findMatchingCatalogueMaterial(exactAct, multiCables);
      expect(resExact.isMapped).toBe(true);
      expect(resExact.material?.id).toBe('mat-c1');

      // Ambiguous without exact match
      const ambiguousAct: Activity = {
        ...cableActivity,
        name: 'General Laying',
      };
      const resAmbiguous = findMatchingCatalogueMaterial(ambiguousAct, multiCables);
      expect(resAmbiguous.isMapped).toBe(false);
      expect(resAmbiguous.reason).toContain('Multiple catalogue materials match');
    });
  });

  describe('isMatchingConsumedMaterial', () => {
    const cableActivity: Activity = {
      id: 'act-cabling',
      name: 'Cable Pulling',
      category: 'cable',
      unit_of_measure: 'metres',
      approved_rate: 10,
      is_active: true,
    };

    const mockCatalogue: CatalogueMaterial[] = [
      {
        id: 'mat-1',
        name: 'Cat6 Cable 30m',
        category: 'cable',
        unit_of_measure: 'mtr',
        purchase_approval_limit: 1000,
        is_active: true,
      },
      {
        id: 'mat-2',
        name: 'RJ45 Connectors',
        category: 'accessories',
        unit_of_measure: 'pcs',
        purchase_approval_limit: 500,
        is_active: true,
      },
    ];

    const matchingTx: MaterialTransaction = {
      id: 'tx-1',
      daily_work_entry_id: 'entry-1',
      material_id: 'mat-1',
      transaction_type: 'consumed',
      item_name: 'Cat6 Cable 30m',
      quantity: 1,
      amount: 0,
      is_high_value: false,
      status: 'draft',
      created_at: '2026-10-28T10:00:00Z',
    };

    it('matches consumed material transaction with matching catalogue material', () => {
      expect(isMatchingConsumedMaterial(cableActivity, matchingTx, mockCatalogue)).toBe(true);
    });

    it('is resilient to parameter order (tx, activity)', () => {
      expect(isMatchingConsumedMaterial(matchingTx, cableActivity, mockCatalogue)).toBe(true);
    });

    it('never synchronizes purchased material transactions', () => {
      const purchasedTx: MaterialTransaction = {
        ...matchingTx,
        transaction_type: 'purchased',
        amount: 250,
      };
      expect(isMatchingConsumedMaterial(cableActivity, purchasedTx, mockCatalogue)).toBe(false);
    });

    it('never synchronizes unrelated materials (e.g. accessories or tools)', () => {
      const unrelatedTx: MaterialTransaction = {
        ...matchingTx,
        material_id: 'mat-2',
        item_name: 'RJ45 Connectors',
      };
      expect(isMatchingConsumedMaterial(cableActivity, unrelatedTx, mockCatalogue)).toBe(false);
    });

    it('safely handles missing or null inputs', () => {
      expect(isMatchingConsumedMaterial(null, matchingTx, mockCatalogue)).toBe(false);
      expect(isMatchingConsumedMaterial(cableActivity, null, mockCatalogue)).toBe(false);
    });
  });
});
