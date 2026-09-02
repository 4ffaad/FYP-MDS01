"use client";

import { HugeiconsIcon, type HugeiconsIconProps } from "@hugeicons/react";
import {
  Activity04Icon,
  Alert02Icon,
  ArrowLeft02Icon,
  ArrowRight02Icon,
  Cancel01Icon,
  Clock01Icon,
  DashboardSquare01Icon,
  Delete02Icon,
  InformationCircleIcon,
  Loading03Icon,
  Menu01Icon,
  Refresh01Icon,
  ShieldCheckIcon,
  SquareLock02Icon,
  Tick02Icon,
  Upload03Icon,
  Zip01Icon,
} from "@hugeicons/core-free-icons";

type IconName =
  | "upload"
  | "list"
  | "shield"
  | "lock"
  | "arrow"
  | "back"
  | "clock"
  | "spinner"
  | "check"
  | "alert"
  | "chevron"
  | "file"
  | "refresh"
  | "info"
  | "activity"
  | "trash"
  | "menu"
  | "close";

const iconMap = {
  upload: Upload03Icon,
  list: DashboardSquare01Icon,
  shield: ShieldCheckIcon,
  lock: SquareLock02Icon,
  arrow: ArrowRight02Icon,
  back: ArrowLeft02Icon,
  clock: Clock01Icon,
  spinner: Loading03Icon,
  check: Tick02Icon,
  alert: Alert02Icon,
  chevron: ArrowRight02Icon,
  file: Zip01Icon,
  refresh: Refresh01Icon,
  info: InformationCircleIcon,
  activity: Activity04Icon,
  trash: Delete02Icon,
  menu: Menu01Icon,
  close: Cancel01Icon,
} as const;

/** Render one consistent Hugeicons stroke icon for product controls and states. */
export function Icon({
  name,
  className = "size-5",
  weight = name === "spinner" ? "bold" : "regular",
  ...props
}: {
  name: IconName;
  className?: string;
  weight?: "regular" | "bold";
} & Omit<HugeiconsIconProps, "icon" | "size" | "strokeWidth">) {
  return (
    <HugeiconsIcon
      {...props}
      icon={iconMap[name]}
      className={className}
      size="1em"
      color="currentColor"
      strokeWidth={weight === "bold" ? 2 : 1.75}
      aria-hidden="true"
    />
  );
}
