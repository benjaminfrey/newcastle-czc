import {
  IconArmchair, IconArrowDown, IconArrowLeft, IconArrowRight, IconArrowUp, IconBuilding, IconBuildingCottage,
  IconBuildingStore, IconBuildingWarehouse, IconCarGarage, IconCopy, IconDots, IconFileAlert, IconHammer, IconHelpCircle,
  IconHome, IconHomePlus, IconLayoutGrid, IconMap2, IconPaint, IconPhoto, IconPlus, IconRoad, IconShovel, IconSignature,
  IconSquare, IconStairs, IconTractor, IconUser, type Icon as TablerIcon,
} from "@tabler/icons-react";

// The outline icons the portal draws (task-list brief §5): the forms' vocabulary
// (portal/api/portal_api/forms/icons.txt) plus the task list's and the buttons'. Only these are
// imported, so the bundle carries only these.
const ICONS: Record<string, TablerIcon> = {
  "armchair": IconArmchair, "arrow-down": IconArrowDown, "arrow-left": IconArrowLeft, "arrow-right": IconArrowRight,
  "arrow-up": IconArrowUp, "building": IconBuilding, "building-cottage": IconBuildingCottage,
  "building-store": IconBuildingStore, "building-warehouse": IconBuildingWarehouse, "car-garage": IconCarGarage,
  "copy": IconCopy, "dots": IconDots, "file-alert": IconFileAlert, "hammer": IconHammer, "help-circle": IconHelpCircle,
  "home": IconHome, "home-plus": IconHomePlus, "layout-grid": IconLayoutGrid, "map-2": IconMap2, "paint": IconPaint,
  "photo": IconPhoto, "plus": IconPlus, "road": IconRoad, "shovel": IconShovel, "signature": IconSignature,
  "square": IconSquare, "stairs": IconStairs, "tractor": IconTractor, "user": IconUser,
};
export const ICON_NAMES = Object.keys(ICONS);

export default function Icon({ name, size = 18, className }: { name: string; size?: number; className?: string }) {
  const Drawn = ICONS[name];
  if (!Drawn) {
    console.warn(`No icon named ${name}`); // the forms' loader refuses unknown names; this catches the app's own
    return null;
  }
  return <Drawn size={size} stroke={1.75} aria-hidden="true" className={`shrink-0 ${className ?? ""}`} />;
}
