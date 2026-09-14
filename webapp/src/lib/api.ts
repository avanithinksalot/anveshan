export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000';

export const TOKEN_KEY = 'mplads_jwt';

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string | null): void => {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
};

export const ROLE_HOME: Record<string, string> = {
  ministry: '/ministry',
  state_nodal: '/state-nodal',
  district_authority: '/da',
  mp: '/mp',
  auditor: '/auditor',
};

export const homeFor = (role?: string | null): string => ROLE_HOME[role ?? ''] ?? '/da';

// Rich Mock Data across 14+ Indian States for Standalone Dynamic Prototype Resilience
export const MOCK_ALERTS_LIST = [
  {
    work_id: 'WS/MP005/2025-2026/183589',
    risk_score: 98.0,
    risk_tier: 'High',
    state: 'Gujarat',
    ida: 'KHEDA(DISTRICT COLLECTOR KHEDA_IDA)',
    mp_name: 'Devusinh Jesingbhai Chauhan',
    work_category_suffix: 'General Infrastructure',
    work_description: 'Construction of Community Hall and Drainage System in Kheda Tehsil',
    sanction_amount: 5800000,
    disbursed_amount: 5800000,
    work_status: 'Sanctioned',
    shap_reason: 'High-risk work flagged due to work being in non-terminal stage for 410 days (1-year rule breach); recommended amount diverges from category range.',
    bypass_ml: true,
  },
  {
    work_id: 'WS/MP104/2022-23/0482',
    risk_score: 94.6,
    risk_tier: 'High',
    state: 'Uttar Pradesh',
    ida: 'Bareilly',
    mp_name: 'Shri Santosh Kumar Gangwar',
    work_category_suffix: 'Roads & Bridges',
    work_description: 'Construction of CC road and drain from Main Marg to Public Health Center in Village Bhojipura',
    sanction_amount: 4850000,
    disbursed_amount: 5120000,
    work_status: 'Sanctioned',
    shap_reason: 'Flagged due to 340% cost deviation from category median and vendor active across 6 districts. Stalled for 410 days (1-year rule breach).',
    bypass_ml: true,
  },
  {
    work_id: 'WS/MP201/2021-22/1129',
    risk_score: 89.2,
    risk_tier: 'High',
    state: 'Uttar Pradesh',
    ida: 'Lucknow',
    mp_name: 'Shri Rajnath Singh',
    work_category_suffix: 'Drinking Water',
    work_description: 'Installation of 25 High-Cap Solar Submersible Handpumps in Ward 14 Gomti Nagar',
    sanction_amount: 3200000,
    disbursed_amount: 3200000,
    work_status: 'Completed',
    shap_reason: 'Flagged due to perceptual image hash collision with work WS/MP104/2020-21/0081 (reused completion photo).',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP342/2020-21/0890',
    risk_score: 88.4,
    risk_tier: 'High',
    state: 'Maharashtra',
    ida: 'Pune',
    mp_name: 'Shri Girish Bapat',
    work_category_suffix: 'Sanitation',
    work_description: 'Construction of Public Toilet Complex near City Bus Stand Ward 8',
    sanction_amount: 2800000,
    disbursed_amount: 2800000,
    work_status: 'Vendor ID',
    shap_reason: 'Flagged due to repeat contractor concentration score (vendor paid across 12 distinct IDAs).',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP512/2022-23/0112',
    risk_score: 87.1,
    risk_tier: 'High',
    state: 'Bihar',
    ida: 'Patna',
    mp_name: 'Shri Ravi Shankar Prasad',
    work_category_suffix: 'Irrigation & Canal',
    work_description: 'Renovation and desilting of Gram Panchayat Water Canal Line in Phulwari Sharif',
    sanction_amount: 6200000,
    disbursed_amount: 5900000,
    work_status: 'Completed',
    shap_reason: 'Flagged due to expense disbursement spike in final 14 days of FY and 210% material cost outlier.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP088/2023-24/0045',
    risk_score: 86.8,
    risk_tier: 'High',
    state: 'Uttar Pradesh',
    ida: 'Bareilly',
    mp_name: 'Shri Santosh Kumar Gangwar',
    work_category_suffix: 'Education & Community',
    work_description: 'Construction of Community Hall and Reading Room at Gram Panchayat Nawabganj',
    sanction_amount: 7500000,
    disbursed_amount: 7500000,
    work_status: 'Physical Inspection',
    shap_reason: 'Flagged due to description cosine similarity 0.94 with existing sanctioned project in adjacent constituency.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP405/2021-22/0312',
    risk_score: 84.5,
    risk_tier: 'High',
    state: 'West Bengal',
    ida: 'Kolkata North',
    mp_name: 'Shri Sudip Bandyopadhyay',
    work_category_suffix: 'Health & Infrastructure',
    work_description: 'Supply and installation of ICU Ventilators for Municipal Urban Hospital Ward 22',
    sanction_amount: 11500000,
    disbursed_amount: 11500000,
    work_status: 'Completed',
    shap_reason: 'Flagged due to unlisted vendor supplier mismatch and 180% unit cost deviation.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP180/2022-23/0741',
    risk_score: 83.2,
    risk_tier: 'High',
    state: 'Madhya Pradesh',
    ida: 'Bhopal',
    mp_name: 'Sadhvi Pragya Singh Thakur',
    work_category_suffix: 'Roads & Bridges',
    work_description: 'Asphalt road resurfacing from Airport Road to Ayodhya Bypass Circle',
    sanction_amount: 8900000,
    disbursed_amount: 8900000,
    work_status: 'Sanctioned',
    shap_reason: 'Flagged due to 1-year rule violation (open 425 days post sanction without physical milestone).',
    bypass_ml: true,
  },
  {
    work_id: 'WS/MP005/2024-25/11024',
    risk_score: 61.5,
    risk_tier: 'Medium',
    state: 'Gujarat',
    ida: 'KHEDA(DISTRICT COLLECTOR KHEDA_IDA)',
    mp_name: 'Devusinh Jesingbhai Chauhan',
    work_category_suffix: 'Drinking Water',
    work_description: 'Augmentation of village pipeline and water tank in Nadiad block',
    sanction_amount: 1800000,
    disbursed_amount: 1800000,
    work_status: 'Physical Inspection',
    shap_reason: 'Medium risk: minor 45-day delay in disbursement schedule; contractor concentration within normal baseline.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP104/2023-24/0991',
    risk_score: 64.2,
    risk_tier: 'Medium',
    state: 'Uttar Pradesh',
    ida: 'Bareilly',
    mp_name: 'Shri Santosh Kumar Gangwar',
    work_category_suffix: 'Roads & Bridges',
    work_description: 'Interlocking tiles road installation from Station Road to Girls High School',
    sanction_amount: 2400000,
    disbursed_amount: 2400000,
    work_status: 'Sanctioned',
    shap_reason: 'Medium risk: slight timeline delay (290 days) and minor contractor concentration ratio.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP099/2022-23/0334',
    risk_score: 58.1,
    risk_tier: 'Medium',
    state: 'Uttar Pradesh',
    ida: 'Varanasi',
    mp_name: 'Shri Narendra Modi',
    work_category_suffix: 'Health & Infrastructure',
    work_description: 'Supply of Digital X-Ray Diagnostic Equipment to District Civil Hospital',
    sanction_amount: 12500000,
    disbursed_amount: 12500000,
    work_status: 'Completed',
    shap_reason: 'Medium risk: high sanction value relative to district baseline, vendor individual flag.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP311/2022-23/0411',
    risk_score: 55.4,
    risk_tier: 'Medium',
    state: 'Kerala',
    ida: 'Thiruvananthapuram',
    mp_name: 'Shri Shashi Tharoor',
    work_category_suffix: 'Education & Community',
    work_description: 'Public Library Reading Room construction in Kazhakkoottam',
    sanction_amount: 4200000,
    disbursed_amount: 4200000,
    work_status: 'Physical Inspection',
    shap_reason: 'Medium risk: moderate cost elevation over regional average.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP418/2021-22/0209',
    risk_score: 51.8,
    risk_tier: 'Medium',
    state: 'Punjab',
    ida: 'Ludhiana',
    mp_name: 'Shri Ravneet Singh Bittu',
    work_category_suffix: 'Parks & Public Amenities',
    work_description: 'Open Gym and Sports Equipment setup at Model Town Park',
    sanction_amount: 1900000,
    disbursed_amount: 1900000,
    work_status: 'Sanctioned',
    shap_reason: 'Medium risk: vendor name variance flag.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP519/2023-24/0088',
    risk_score: 49.3,
    risk_tier: 'Medium',
    state: 'Odisha',
    ida: 'Bhubaneswar',
    mp_name: 'Smt. Aparajita Sarangi',
    work_category_suffix: 'Drinking Water',
    work_description: 'Installation of Solar Overhead Water Tank at Gram Panchayat Jatni',
    sanction_amount: 2700000,
    disbursed_amount: 2700000,
    work_status: 'Completed',
    shap_reason: 'Medium risk: completion duration 320 days.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP622/2022-23/0145',
    risk_score: 46.0,
    risk_tier: 'Medium',
    state: 'Assam',
    ida: 'Guwahati',
    mp_name: 'Queen Oja',
    work_category_suffix: 'Roads & Bridges',
    work_description: 'Culvert construction and road strengthening on Zoo Road Extension',
    sanction_amount: 3600000,
    disbursed_amount: 3600000,
    work_status: 'Sanctioned',
    shap_reason: 'Medium risk: slight timeline lag.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP005/2023-24/04012',
    risk_score: 15.4,
    risk_tier: 'Low',
    state: 'Gujarat',
    ida: 'KHEDA(DISTRICT COLLECTOR KHEDA_IDA)',
    mp_name: 'Devusinh Jesingbhai Chauhan',
    work_category_suffix: 'Parks & Public Amenities',
    work_description: 'Installation of LED Streetlights along Kheda Gram Panchayat Main Marg',
    sanction_amount: 450000,
    disbursed_amount: 450000,
    work_status: 'Completed',
    shap_reason: 'Low risk: verified completion geotags, standard unit pricing, zero anomaly flags.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP544/2023-24/0019',
    risk_score: 24.5,
    risk_tier: 'Low',
    state: 'Uttar Pradesh',
    ida: 'Bareilly',
    mp_name: 'Shri Santosh Kumar Gangwar',
    work_category_suffix: 'Drinking Water',
    work_description: 'Submersible Pump installation at Primary School Faridpur',
    sanction_amount: 650000,
    disbursed_amount: 650000,
    work_status: 'Completed',
    shap_reason: 'Low risk: fully compliant timeline, standard category median pricing.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP201/2023-24/0055',
    risk_score: 19.8,
    risk_tier: 'Low',
    state: 'Uttar Pradesh',
    ida: 'Lucknow',
    mp_name: 'Shri Rajnath Singh',
    work_category_suffix: 'Education & Community',
    work_description: 'Furniture and Smart Board supply to Municipal Primary School Ward 5',
    sanction_amount: 850000,
    disbursed_amount: 850000,
    work_status: 'Completed',
    shap_reason: 'Low risk: transparent e-tender procurement, physical audit verified.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP342/2023-24/0112',
    risk_score: 22.1,
    risk_tier: 'Low',
    state: 'Maharashtra',
    ida: 'Pune',
    mp_name: 'Shri Girish Bapat',
    work_category_suffix: 'Sanitation',
    work_description: 'Public Handwashing Stations setup near Pune Railway Station',
    sanction_amount: 520000,
    disbursed_amount: 520000,
    work_status: 'Completed',
    shap_reason: 'Low risk: completed within 60 days, verified expenditure vouchers.',
    bypass_ml: false,
  },
  {
    work_id: 'WS/MP001/2022-23/0008',
    risk_score: 18.2,
    risk_tier: 'Low',
    state: 'Delhi',
    ida: 'New Delhi',
    mp_name: 'Shri Hardeep Singh Puri',
    work_category_suffix: 'Parks & Public Amenities',
    work_description: 'Solar LED streetlight installation along Ring Road Community Park',
    sanction_amount: 1400000,
    disbursed_amount: 1400000,
    work_status: 'Completed',
    shap_reason: 'Low risk: verified geotag and zero duplicate indicators.',
    bypass_ml: false,
  },
];


export async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const tk = getToken();
  if (tk) headers.set('Authorization', 'Bearer ' + tk);

  try {
    const r = await fetch(url, { ...init, headers });
    if (r.ok) return (await r.json()) as T;
  } catch {
    /* backend offline or network error fallback */
  }

  // Graceful fallback for dynamic offline prototype mode
  return getMockResponse<T>(url);
}

function getMockResponse<T>(url: string): T {
  const parsed = new URL(url, 'http://localhost:8000');
  const path = parsed.pathname;

  if (path.startsWith('/works/') && path.endsWith('/risk')) {
    const work_id = decodeURIComponent(path.slice('/works/'.length, -'/risk'.length));
    const found = MOCK_ALERTS_LIST.find((a) => a.work_id === work_id) || MOCK_ALERTS_LIST[0];
    return {
      work_id: found.work_id,
      risk_score: found.risk_score,
      risk_tier: found.risk_tier,
      bypass_ml: found.bypass_ml,
      source_table: 'Works_Sanctioned',
      state: found.state,
      ida: found.ida,
      mp_name: found.mp_name,
      work_category_suffix: found.work_category_suffix,
      work_description: found.work_description,
      sanction_amount: found.sanction_amount,
      disbursed_amount: found.disbursed_amount,
      work_status: found.work_status,
      shap_reason: found.shap_reason,
      components: {
        xgboost: found.risk_score > 70 ? 0.8842 : 0.2415,
        isolforest: found.risk_score > 70 ? 0.7910 : 0.1802,
        similarity: found.risk_score > 80 ? 0.9400 : 0.0520,
        composite_ml: found.risk_score,
      },
    } as unknown as T;
  }

  if (path.startsWith('/alerts')) {
    const tier = parsed.searchParams.get('tier');
    const state = parsed.searchParams.get('state');
    const ida = parsed.searchParams.get('ida');
    const mp = parsed.searchParams.get('mp');

    let filtered = [...MOCK_ALERTS_LIST];
    if (tier) filtered = filtered.filter((a) => a.risk_tier.toLowerCase() === tier.toLowerCase());
    if (state) filtered = filtered.filter((a) => a.state.toLowerCase() === state.toLowerCase());
    if (ida) filtered = filtered.filter((a) => a.ida.toLowerCase().includes(ida.toLowerCase()));
    if (mp) filtered = filtered.filter((a) => a.mp_name.toLowerCase().includes(mp.toLowerCase()));

    return {
      count: filtered.length,
      filters: { tier, state, ida, mp },
      alerts: filtered,
    } as unknown as T;
  }

  if (path.startsWith('/audit/actions')) {
    return {
      role: 'auditor',
      counts: { total: 4, cleared: 1, escalated: 2, confirmed: 1 },
      actions: [
        {
          id: 101,
          work_id: 'WS/MP104/2022-23/0482',
          action: 'confirmed',
          note: 'Physical inspection confirmed zero progress despite 100% fund disbursement.',
          reviewer: 'DA-BAREILLY@mspi',
          risk_score_at: 94.6,
          risk_tier_at: 'High',
          recorded_at: new Date(Date.now() - 3600000).toISOString(),
          work_description: 'Construction of CC road and drain from Main Marg to Public Health Center',
          state: 'Uttar Pradesh',
          ida: 'Bareilly',
          mp_name: 'Shri Santosh Kumar Gangwar',
          sanction_amount: 4850000,
          work_status: 'Sanctioned',
        },
        {
          id: 102,
          work_id: 'WS/MP201/2021-22/1129',
          action: 'escalated',
          note: 'Image hash collision flagged for state nodal review.',
          reviewer: 'DA-LUCKNOW@mspi',
          risk_score_at: 89.2,
          risk_tier_at: 'High',
          recorded_at: new Date(Date.now() - 7200000).toISOString(),
          work_description: 'Installation of 25 High-Cap Solar Submersible Handpumps in Ward 14',
          state: 'Uttar Pradesh',
          ida: 'Lucknow',
          mp_name: 'Shri Rajnath Singh',
          sanction_amount: 3200000,
          work_status: 'Completed',
        },
        {
          id: 103,
          work_id: 'WS/MP544/2023-24/0019',
          action: 'cleared',
          note: 'Verified physical completion certificate and geotags.',
          reviewer: 'DA-BAREILLY@mspi',
          risk_score_at: 24.5,
          risk_tier_at: 'Low',
          recorded_at: new Date(Date.now() - 14400000).toISOString(),
          work_description: 'Submersible Pump installation at Primary School Faridpur',
          state: 'Uttar Pradesh',
          ida: 'Bareilly',
          mp_name: 'Shri Santosh Kumar Gangwar',
          sanction_amount: 650000,
          work_status: 'Completed',
        },
      ],
    } as unknown as T;
  }

  if (path.startsWith('/cases/')) {
    return { status: 'recorded', stored: 'mock://postgres' } as unknown as T;
  }

  if (path.startsWith('/dashboard/summary')) {
    return {
      role: parsed.searchParams.get('role') || 'ministry',
      scope: 'National',
      totals: {
        works: 35200,
        total_sanctioned: 18450000000,
        high_works: 1240,
        hard_violations: 482,
      },
      tiers: { low: 24500, medium: 9460, high: 1240 },
      top_states_by_high: {
        'Uttar Pradesh': 380,
        Maharashtra: 240,
        Bihar: 190,
        'West Bengal': 140,
        'Madhya Pradesh': 110,
        Rajasthan: 95,
        TamilNadu: 85,
        Gujarat: 60,
      },
      districts_by_risk: {
        Bareilly: 42,
        Lucknow: 38,
        Varanasi: 31,
        Gorakhpur: 27,
        Kanpur: 24,
        Agra: 19,
      },
      works: MOCK_ALERTS_LIST,
    } as unknown as T;
  }

  return {} as unknown as T;
}

export const riskColor = (tier?: string | null): string => {
  switch (tier) {
    case 'Low':    return '#166534';
    case 'Medium': return '#B45309';
    case 'High':   return '#B91C1C';
    default:       return '#7A967A';
  }
};

export const esc = (s: unknown): string =>
  String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));

export const amt = (v?: number | null): string =>
  v == null ? '—' : '\u20B9' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 });

export const now2 = (t?: string | null): string =>
  t ? String(t).replace('T', ' ').replace(/\.\d+Z?$/, '') : '—';