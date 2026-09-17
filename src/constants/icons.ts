import type { LucideIcon } from 'lucide-react';
import {
  BookOpen,
  Briefcase,
  BrainCircuit,
  Building2,
  Code,
  Dna,
  GraduationCap,
  HeartHandshake,
  Hotel,
  Info,
  Languages,
  LayoutDashboard,
  Megaphone,
  Music,
  Newspaper,
  Palette,
  Pill,
  Plane,
  Ruler,
  Scale,
  ShieldCheck,
  Sparkles,
  Sprout,
  Stethoscope,
  TestTube,
  TrendingUp,
  Truck,
  UserCheck,
  Wallet,
  Wrench,
  Zap
} from 'lucide-react';

export const MENU_ICONS_MAP = {
  dashboard: LayoutDashboard,
  profile: UserCheck,
  recommendation: Sparkles,
  development: TrendingUp,
  library: Briefcase,
  careers: Briefcase,
  about: Info,
  guide: BookOpen
} satisfies Record<string, LucideIcon>;

export const CAREER_ICONS_MAP = {
  it_software: Code,
  ai_data: BrainCircuit,
  automation_ee: Zap,
  mechanical_semiconductor: Wrench,
  business_admin: Building2,
  finance_banking: Wallet,
  marketing_media: Megaphone,
  logistics_supply: Truck,
  design_uiux: Palette,
  medicine_health: Stethoscope,
  pharmacy: Pill,
  architecture_civil: Ruler,
  law_legal: Scale,
  languages_trans: Languages,
  education_pedagogy: GraduationCap,
  psychology_social: HeartHandshake,
  hospitality_tourism: Hotel,
  biotech_food: Dna,
  chemistry_materials: TestTube,
  agriculture_env: Sprout,
  aviation_maritime: Plane,
  journalism_media: Newspaper,
  arts_music: Music,
  security_defense: ShieldCheck
} satisfies Record<string, LucideIcon>;

export type MenuIconName = keyof typeof MENU_ICONS_MAP;
export type CareerIconName = keyof typeof CAREER_ICONS_MAP;
