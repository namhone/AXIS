import { HelpCircle } from 'lucide-react';
import type { SVGProps } from 'react';
import { CAREER_ICONS_MAP, type CareerIconName } from '../../constants/icons';

export interface CareerIconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  categoryId: string;
  size?: number | string;
  strokeWidth?: number;
}

export function CareerIcon({
  categoryId,
  size = 24,
  className,
  strokeWidth = 1.75,
  ...props
}: CareerIconProps) {
  const Icon = CAREER_ICONS_MAP[categoryId as CareerIconName] || HelpCircle;
  return <Icon size={size} className={className} strokeWidth={strokeWidth} aria-hidden="true" {...props} />;
}
