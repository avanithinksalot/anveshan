// Simplified GeoJSON for India's states — coordinates are approximate but geographically faithful.
// Format: GeoJSON FeatureCollection, WGS84 (lon, lat) pairs.

export interface StateFeature {
  type: 'Feature';
  properties: { name: string; code: string };
  geometry: { type: 'Polygon' | 'MultiPolygon'; coordinates: number[][][][] | number[][][] };
}

export interface IndiaGeoJSON {
  type: 'FeatureCollection';
  features: StateFeature[];
}

function poly(coords: number[][]): StateFeature['geometry'] {
  return { type: 'Polygon', coordinates: [coords] };
}

export const INDIA_STATES: IndiaGeoJSON = {
  type: 'FeatureCollection',
  features: [
    // ── North ────────────────────────────────────────────────────────────
    {
      type: 'Feature',
      properties: { name: 'Jammu & Kashmir', code: 'JK' },
      geometry: poly([
        [73.9,37.0],[75.5,37.0],[78.5,37.0],[79.5,35.5],[79.5,34.0],[78.0,33.5],
        [76.5,33.5],[75.5,34.0],[73.9,35.5],[73.9,37.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Ladakh', code: 'LA' },
      geometry: poly([
        [75.5,37.0],[80.5,37.0],[82.0,36.0],[80.5,34.0],[79.5,34.0],[79.5,35.5],[75.5,37.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Himachal Pradesh', code: 'HP' },
      geometry: poly([
        [75.5,34.0],[78.0,33.5],[79.5,34.0],[79.5,31.5],[78.0,31.0],[77.0,31.5],
        [76.5,32.0],[75.5,32.5],[75.5,34.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Punjab', code: 'PB' },
      geometry: poly([
        [73.9,32.5],[75.5,32.5],[76.5,32.0],[77.0,31.5],[76.0,30.5],[75.0,30.2],
        [73.9,30.5],[73.9,32.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Uttarakhand', code: 'UK' },
      geometry: poly([
        [78.0,31.0],[79.5,31.5],[80.5,31.0],[81.0,30.5],[80.0,29.5],[79.0,29.0],
        [78.0,30.0],[78.0,31.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Haryana', code: 'HR' },
      geometry: poly([
        [75.0,30.2],[76.0,30.5],[77.0,31.5],[78.0,30.0],[77.5,28.5],[77.0,28.0],
        [76.0,28.0],[74.5,29.0],[75.0,30.2],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Delhi', code: 'DL' },
      geometry: poly([
        [76.8,28.9],[77.4,28.9],[77.4,28.4],[76.8,28.4],[76.8,28.9],
      ]),
    },

    // ── North-Central ────────────────────────────────────────────────────
    {
      type: 'Feature',
      properties: { name: 'Uttar Pradesh', code: 'UP' },
      geometry: poly([
        [77.0,30.5],[78.0,30.0],[80.5,31.0],[84.0,27.5],[84.5,24.5],[82.0,24.0],
        [79.0,24.5],[77.5,26.0],[77.0,28.0],[77.0,30.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Rajasthan', code: 'RJ' },
      geometry: poly([
        [69.5,30.2],[73.0,30.5],[75.0,30.2],[76.0,30.5],[77.0,28.0],[77.5,26.0],
        [76.5,25.0],[74.0,24.0],[70.5,24.0],[69.5,25.5],[69.5,30.2],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Gujarat', code: 'GJ' },
      geometry: poly([
        [68.2,24.5],[70.5,24.5],[71.5,24.0],[74.0,24.0],[72.5,22.0],
        [72.5,21.0],[70.0,21.0],[69.0,22.0],[68.2,23.0],[68.2,24.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Madhya Pradesh', code: 'MP' },
      geometry: poly([
        [74.0,26.5],[77.5,26.0],[79.0,26.0],[82.0,24.0],[84.5,24.5],[83.0,22.0],
        [80.5,18.5],[79.0,18.5],[76.5,18.5],[74.0,21.0],[74.0,26.5],
      ]),
    },

    // ── East ─────────────────────────────────────────────────────────────
    {
      type: 'Feature',
      properties: { name: 'Bihar', code: 'BR' },
      geometry: poly([
        [84.0,27.5],[87.5,27.5],[88.0,26.5],[87.0,25.0],[84.5,24.5],[84.0,27.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Jharkhand', code: 'JH' },
      geometry: poly([
        [84.5,24.5],[87.0,25.0],[87.0,22.5],[84.5,21.5],[83.0,22.0],[84.5,24.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'West Bengal', code: 'WB' },
      geometry: poly([
        [88.0,26.5],[89.5,27.0],[89.5,25.0],[88.5,22.5],[86.5,21.5],[87.0,22.5],
        [87.0,25.0],[88.0,26.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Odisha', code: 'OD' },
      geometry: poly([
        [82.0,22.5],[84.5,21.5],[86.5,21.5],[87.0,20.0],[85.5,18.0],
        [83.5,17.5],[81.5,18.5],[82.0,22.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Chhattisgarh', code: 'CG' },
      geometry: poly([
        [80.5,24.0],[82.0,24.0],[83.0,22.0],[84.5,21.5],[83.0,19.0],
        [80.5,18.5],[80.5,24.0],
      ]),
    },

    // ── West/Deccan ──────────────────────────────────────────────────────
    {
      type: 'Feature',
      properties: { name: 'Maharashtra', code: 'MH' },
      geometry: poly([
        [72.5,21.0],[74.0,21.0],[76.5,18.5],[79.0,18.5],[80.5,18.5],
        [80.5,16.5],[78.0,15.5],[76.0,16.0],[74.5,17.5],[72.5,20.0],[72.5,21.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Goa', code: 'GA' },
      geometry: poly([
        [73.7,15.8],[74.5,15.8],[74.5,14.9],[73.7,14.9],[73.7,15.8],
      ]),
    },

    // ── South ────────────────────────────────────────────────────────────
    {
      type: 'Feature',
      properties: { name: 'Telangana', code: 'TS' },
      geometry: poly([
        [77.5,19.5],[79.0,18.5],[80.5,18.5],[80.5,16.5],[79.0,17.0],
        [77.5,17.5],[77.5,19.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Andhra Pradesh', code: 'AP' },
      geometry: poly([
        [77.0,15.5],[78.0,15.5],[80.5,16.5],[84.5,19.0],[83.5,17.5],
        [80.0,13.0],[79.0,12.5],[77.5,13.0],[77.0,15.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Karnataka', code: 'KA' },
      geometry: poly([
        [74.5,18.0],[76.0,16.0],[78.0,15.5],[77.5,13.0],[79.0,12.5],
        [77.5,11.5],[75.0,11.5],[74.0,13.0],[73.5,15.0],[74.5,18.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Kerala', code: 'KL' },
      geometry: poly([
        [74.0,13.0],[75.0,11.5],[77.5,8.5],[76.5,8.4],[74.0,11.0],[74.0,13.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Tamil Nadu', code: 'TN' },
      geometry: poly([
        [77.0,13.5],[79.5,13.5],[80.5,12.0],[80.0,8.6],[77.5,8.5],
        [77.5,11.5],[77.0,13.5],
      ]),
    },

    // ── Northeast ────────────────────────────────────────────────────────
    {
      type: 'Feature',
      properties: { name: 'Assam', code: 'AS' },
      geometry: poly([
        [89.5,27.0],[93.5,27.5],[95.5,27.0],[95.0,25.5],[92.5,24.5],
        [89.5,24.5],[89.5,27.0],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Arunachal Pradesh', code: 'AR' },
      geometry: poly([
        [91.5,29.5],[97.0,29.5],[97.0,27.0],[95.5,27.0],[93.5,27.5],[91.5,29.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Nagaland', code: 'NL' },
      geometry: poly([
        [93.5,27.5],[95.5,27.0],[95.5,25.5],[93.5,25.5],[93.5,27.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Manipur', code: 'MN' },
      geometry: poly([
        [93.5,25.5],[95.5,25.5],[95.5,23.8],[93.5,23.8],[93.5,25.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Mizoram', code: 'MZ' },
      geometry: poly([
        [92.0,24.5],[93.5,24.5],[93.5,23.8],[92.0,23.2],[92.0,24.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Tripura', code: 'TR' },
      geometry: poly([
        [91.0,24.5],[92.0,24.5],[92.0,23.2],[91.0,23.0],[91.0,24.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Meghalaya', code: 'ML' },
      geometry: poly([
        [89.5,25.5],[92.5,25.5],[92.5,24.5],[89.5,24.5],[89.5,25.5],
      ]),
    },
    {
      type: 'Feature',
      properties: { name: 'Sikkim', code: 'SK' },
      geometry: poly([
        [88.0,27.5],[89.0,27.5],[89.0,26.5],[88.0,26.5],[88.0,27.5],
      ]),
    },
  ],
};

// Risk data mapping — mock values that match our MOCK_ALERTS_LIST state distribution
export const MOCK_STATE_RISK: Record<string, number> = {
  'Uttar Pradesh': 380,
  'Maharashtra': 240,
  'Bihar': 190,
  'West Bengal': 140,
  'Madhya Pradesh': 110,
  'Rajasthan': 95,
  'Tamil Nadu': 85,
  'Gujarat': 60,
  'Andhra Pradesh': 48,
  'Karnataka': 42,
  'Odisha': 38,
  'Punjab': 35,
  'Assam': 30,
  'Telangana': 28,
  'Jharkhand': 25,
  'Chhattisgarh': 22,
  'Haryana': 18,
  'Kerala': 15,
  'Himachal Pradesh': 10,
  'Uttarakhand': 8,
  'Jammu & Kashmir': 6,
  'Goa': 3,
  'Delhi': 12,
  'Arunachal Pradesh': 5,
  'Nagaland': 4,
  'Manipur': 5,
  'Mizoram': 3,
  'Tripura': 4,
  'Meghalaya': 6,
  'Sikkim': 2,
  'Ladakh': 1,
};

// Audit density mock (confirmed irregularities per state)
export const MOCK_STATE_AUDIT: Record<string, number> = {
  'Uttar Pradesh': 18,
  'Maharashtra': 12,
  'Bihar': 9,
  'West Bengal': 7,
  'Madhya Pradesh': 5,
  'Rajasthan': 4,
  'Tamil Nadu': 3,
  'Gujarat': 3,
  'Andhra Pradesh': 2,
  'Karnataka': 2,
  'Odisha': 2,
  'Punjab': 1,
  'Assam': 2,
  'Telangana': 1,
  'Jharkhand': 1,
};
