import { Briefcase } from 'lucide-react';
import type { SVGProps } from 'react';
import { MENU_ICONS_MAP, type MenuIconName } from '../../constants/icons';

export interface MenuIconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: string;
  size?: number | string;
  strokeWidth?: number;
}

export function MenuIcon({
  name,
  size = 24,
  className,
  strokeWidth = 1.75,
  ...props
}: MenuIconProps) {
  const Icon = MENU_ICONS_MAP[name as MenuIconName] || Briefcase;
  return <Icon size={size} className={className} strokeWidth={strokeWidth} aria-hidden="true" {...props} />;
}
