"use client";

import {
  ArrowClockwise,
  ArrowLeft,
  ArrowRight,
  CaretRight,
  CheckCircle,
  Clock,
  FileZip,
 Info,
 List,
  ListBullets,
 LockKey,
 Pulse,
 ShieldCheck,
 SpinnerGap,
 UploadSimple,
 WarningCircle,
 Trash,
 X,
 type IconProps,
} from "@phosphor-icons/react";

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
  upload: UploadSimple,
  list: ListBullets,
  shield: ShieldCheck,
  lock: LockKey,
  arrow: ArrowRight,
  back: ArrowLeft,
  clock: Clock,
  spinner: SpinnerGap,
  check: CheckCircle,
  alert: WarningCircle,
  chevron: CaretRight,
  file: FileZip,
  refresh: ArrowClockwise,
  info: Info,
  activity: Pulse,
  trash: Trash,
  menu: List,
  close: X,
} as const;

/** Render one consistent Phosphor icon for product controls and states. */
export function Icon({ name, className = "size-5", weight = name === "spinner" ? "bold" : "regular", ...props }: { name: IconName; className?: string } & Omit<IconProps, "name">) {
  const Component = iconMap[name];
  return <Component {...props} className={className} size="1em" aria-hidden="true" weight={weight} />;
}
