// ─── Feline Five personality dimensions (Litchfield et al. 2017, PLOS ONE 12(8):e0183455) ───

export interface FelineFive {
  neuroticism: number;    // 0..1
  extraversion: number;   // 0..1
  dominance: number;      // 0..1
  impulsiveness: number;  // 0..1
  agreeableness: number;  // 0..1
}

export type ArchetypeName =
  | 'THE_BOLD_DIPLOMAT'
  | 'THE_CURIOUS_WATCHER'
  | 'THE_ANXIOUS_SKEPTIC'
  | 'THE_ALOOF_SOVEREIGN'
  | 'THE_PLAYFUL_VOLATILE';

export interface Archetype {
  name: ArchetypeName;
  personality: FelineFive;
  habituation_rate: number; // decay of engagement probability per sim-minute
}

// ─── SimCat state machine ───

export type SimCatStateName =
  | 'ABSENT'
  | 'RESTING'
  | 'ALERT'
  | 'CURIOUS'
  | 'APPROACHING'
  | 'ENGAGING'
  | 'OVERSTIMULATED'
  | 'STRESSED'
  | 'RETREATING'
  | 'LEAVING';

export type EarPosition = 'forward' | 'neutral' | 'sideways' | 'flat';
export type TailPosition = 'up' | 'neutral' | 'low' | 'puffed' | 'lashing';
export type BodyPosture = 'relaxed' | 'crouched' | 'arched' | 'frozen';

// Schötz Meowsic categorisation
export type VocalizationType =
  | 'purr'
  | 'trill'
  | 'meow'
  | 'growl'
  | 'hiss'
  | 'yowl';

export interface Vocalization {
  type: VocalizationType;
  intensity: number; // 0..1
}

export interface Position {
  x: number;
  y: number;
}

export interface CatState {
  archetype: ArchetypeName;
  state: SimCatStateName;
  position: Position;
  earPosition: EarPosition;
  tailPosition: TailPosition;
  gazeDirection: Position;
  pupilDilation: number; // 0..1
  bodyPosture: BodyPosture;
  vocalizing: Vocalization | null;
  cssScore: number; // 1..7 (Kessler & Turner 1997)
  tickCount: number;
}

// ─── Agent action space ───

export type AgentActionType =
  | 'idle'
  | 'slow_blink'
  | 'trill'
  | 'soft_purr'
  | 'side_glance'
  | 'pause';

export interface AgentAction {
  type: AgentActionType;
  intensity: number; // 0..1
  duration_ms: number;
}

// ─── Ethogram categories (Kappel et al. 2024, Pets (MDPI), DOI 10.3390/pets1030021) ───

export type EthogramCategory =
  | 'locomotion'
  | 'resting'
  | 'grooming'
  | 'feeding'
  | 'elimination'
  | 'social_affiliative'
  | 'social_agonistic'
  | 'play'
  | 'exploration'
  | 'vocalisation'
  | 'marking'
  | 'other';

export interface EthogramBehaviour {
  id: string;
  name: string;
  category: EthogramCategory;
  description: string;
  source: string; // citation key
}

// ─── Ethics monitor types ───

export interface SessionLog {
  sessionId: string;
  archetypeName: ArchetypeName;
  startTick: number;
  endTick: number;
  cssTrajectory: number[];
  optOutEvents: number; // count of LEAVING/RETREATING transitions
  agentActions: AgentAction[];
  timeInStress: number; // ticks with CSS >= 5
  timeInEngagement: number; // ticks in ENGAGING state
  forcedPauses: number;
  lockedOut: boolean;
}

export interface EthicsState {
  currentSessionLog: SessionLog | null;
  sessionHistory: SessionLog[];
  consecutiveHighCssSessions: number;
  lockedUntilTick: number; // 0 = not locked
  dailySessionMinutes: number;
  dailyCapMinutes: number;
}

// ─── Simulation config ───

export interface SimConfig {
  tickRate: number; // ticks per second (default 10)
  simSpeed: number; // multiplier (1, 5, 20, 100)
  arenaWidth: number;
  arenaHeight: number;
}
