import type { ElementType } from "react";
import {
  Activity,
  Apple,
  Baby,
  Beaker,
  Bone,
  Brain,
  CircleDot,
  Droplets,
  Ear,
  Eye,
  Flame,
  FlaskConical,
  Heart,
  HeartPulse,
  Leaf,
  type LucideIcon,
  Pill,
  Shield,
  ShieldPlus,
  Smile,
  Snowflake,
  Stethoscope,
  Syringe,
  Thermometer,
  Users,
  Vegan,
  Wind,
  Zap,
} from "lucide-react";

export interface CategoryMeta {
  icon: LucideIcon;
  gradient: string;
  accent: string;
}

export const CATEGORY_META: Record<string, CategoryMeta> = {
  // ── Top categories ────────────────────────────────────────
  "Aparato Respiratorio": {
    icon: Wind,
    gradient: "from-sky-500 to-cyan-400",
    accent: "bg-sky-50 text-sky-700 border-sky-200",
  },
  "Sistema Nervioso": {
    icon: Brain,
    gradient: "from-purple-500 to-violet-400",
    accent: "bg-purple-50 text-purple-700 border-purple-200",
  },
  "Analgésicos": {
    icon: Thermometer,
    gradient: "from-red-500 to-rose-400",
    accent: "bg-red-50 text-red-700 border-red-200",
  },
  "Sistema Cardiovascular": {
    icon: Heart,
    gradient: "from-rose-500 to-pink-400",
    accent: "bg-rose-50 text-rose-700 border-rose-200",
  },
  "Antiinfecciosos": {
    icon: Shield,
    gradient: "from-amber-500 to-yellow-400",
    accent: "bg-amber-50 text-amber-700 border-amber-200",
  },
  "Aparato Digestivo": {
    icon: Activity,
    gradient: "from-orange-500 to-amber-400",
    accent: "bg-orange-50 text-orange-700 border-orange-200",
  },
  "Vitaminas y Minerales": {
    icon: Apple,
    gradient: "from-emerald-500 to-green-400",
    accent: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  "Sistema Genitourinario": {
    icon: Droplets,
    gradient: "from-teal-500 to-cyan-400",
    accent: "bg-teal-50 text-teal-700 border-teal-200",
  },
  "Suplementos": {
    icon: Leaf,
    gradient: "from-lime-500 to-green-400",
    accent: "bg-lime-50 text-lime-700 border-lime-200",
  },
  "Dermatología": {
    icon: Droplets,
    gradient: "from-pink-500 to-fuchsia-400",
    accent: "bg-pink-50 text-pink-700 border-pink-200",
  },
  "Diabetes": {
    icon: Syringe,
    gradient: "from-blue-500 to-indigo-400",
    accent: "bg-blue-50 text-blue-700 border-blue-200",
  },
  "Oftalmología": {
    icon: Eye,
    gradient: "from-indigo-500 to-blue-400",
    accent: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
  "Cardiológicos": {
    icon: HeartPulse,
    gradient: "from-red-600 to-rose-500",
    accent: "bg-red-50 text-red-700 border-red-200",
  },
  "Oncología": {
    icon: Stethoscope,
    gradient: "from-violet-600 to-purple-500",
    accent: "bg-violet-50 text-violet-700 border-violet-200",
  },
  "Aparato Locomotor": {
    icon: Bone,
    gradient: "from-stone-500 to-zinc-400",
    accent: "bg-stone-50 text-stone-700 border-stone-200",
  },
  "Antihistamínicos": {
    icon: Flame,
    gradient: "from-fuchsia-500 to-pink-400",
    accent: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200",
  },
  "Leches y Fórmulas": {
    icon: Baby,
    gradient: "from-sky-400 to-blue-300",
    accent: "bg-sky-50 text-sky-700 border-sky-200",
  },
  "Alimentos y Bebidas": {
    icon: Apple,
    gradient: "from-yellow-500 to-orange-400",
    accent: "bg-yellow-50 text-yellow-700 border-yellow-200",
  },
  "Sistema Endocrino": {
    icon: Activity,
    gradient: "from-cyan-500 to-teal-400",
    accent: "bg-cyan-50 text-cyan-700 border-cyan-200",
  },

  // ── Additional categories ─────────────────────────────────
  "Otros": {
    icon: CircleDot,
    gradient: "from-gray-400 to-slate-300",
    accent: "bg-gray-50 text-gray-700 border-gray-200",
  },
  "Sin Categoría": {
    icon: Pill,
    gradient: "from-slate-400 to-gray-300",
    accent: "bg-slate-50 text-slate-600 border-slate-200",
  },
  "Medicamentos": {
    icon: Pill,
    gradient: "from-emerald-600 to-teal-500",
    accent: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  "Protección": {
    icon: ShieldPlus,
    gradient: "from-blue-600 to-sky-500",
    accent: "bg-blue-50 text-blue-700 border-blue-200",
  },
  "Hospitalarios": {
    icon: Stethoscope,
    gradient: "from-slate-500 to-zinc-400",
    accent: "bg-slate-50 text-slate-700 border-slate-200",
  },
  "Sangre": {
    icon: HeartPulse,
    gradient: "from-red-500 to-red-400",
    accent: "bg-red-50 text-red-700 border-red-200",
  },
  "Huesos Y Articulaciones": {
    icon: Bone,
    gradient: "from-amber-500 to-orange-400",
    accent: "bg-amber-50 text-amber-700 border-amber-200",
  },
  "Sistemáticos": {
    icon: Zap,
    gradient: "from-yellow-500 to-amber-400",
    accent: "bg-yellow-50 text-yellow-700 border-yellow-200",
  },
  "Cuidado Para La Familia": {
    icon: Users,
    gradient: "from-teal-500 to-emerald-400",
    accent: "bg-teal-50 text-teal-700 border-teal-200",
  },
  "Homeopatía": {
    icon: FlaskConical,
    gradient: "from-green-500 to-lime-400",
    accent: "bg-green-50 text-green-700 border-green-200",
  },
  "Antigotosos Y Uricosúricos": {
    icon: Beaker,
    gradient: "from-indigo-500 to-violet-400",
    accent: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
  "Antianémicos": {
    icon: HeartPulse,
    gradient: "from-rose-500 to-red-400",
    accent: "bg-rose-50 text-rose-700 border-rose-200",
  },
  "Antitrombóticos": {
    icon: Shield,
    gradient: "from-purple-500 to-indigo-400",
    accent: "bg-purple-50 text-purple-700 border-purple-200",
  },
  "Nutrición Deportiva": {
    icon: Zap,
    gradient: "from-orange-500 to-red-400",
    accent: "bg-orange-50 text-orange-700 border-orange-200",
  },
  "Otológicos": {
    icon: Ear,
    gradient: "from-violet-500 to-purple-400",
    accent: "bg-violet-50 text-violet-700 border-violet-200",
  },
  "Antiespasmódicos Femeninos": {
    icon: Snowflake,
    gradient: "from-pink-400 to-rose-300",
    accent: "bg-pink-50 text-pink-700 border-pink-200",
  },
  "Inmunosupresores": {
    icon: ShieldPlus,
    gradient: "from-cyan-600 to-blue-500",
    accent: "bg-cyan-50 text-cyan-700 border-cyan-200",
  },
  "Naturales": {
    icon: Vegan,
    gradient: "from-green-500 to-emerald-400",
    accent: "bg-green-50 text-green-700 border-green-200",
  },
  "Soluciones": {
    icon: Beaker,
    gradient: "from-sky-500 to-blue-400",
    accent: "bg-sky-50 text-sky-700 border-sky-200",
  },
  "Bucal": {
    icon: Smile,
    gradient: "from-cyan-400 to-sky-300",
    accent: "bg-cyan-50 text-cyan-700 border-cyan-200",
  },
};

export const DEFAULT_META: CategoryMeta = {
  icon: Pill,
  gradient: "from-gray-500 to-slate-400",
  accent: "bg-gray-50 text-gray-700 border-gray-200",
};

export function getCategoryMeta(categoryName: string): CategoryMeta {
  return CATEGORY_META[categoryName] || DEFAULT_META;
}
