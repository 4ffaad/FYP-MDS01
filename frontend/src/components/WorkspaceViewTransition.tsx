"use client";

import type { ReactNode } from "react";
import { MotionConfig, motion } from "motion/react";

/** Crossfade workspace views while keeping an in-progress upload mounted. */
export function WorkspaceViewTransition({
  reviewsVisible,
  upload,
  reviews,
}: {
  reviewsVisible: boolean;
  upload: ReactNode;
  reviews: ReactNode;
}) {
  return (
    <MotionConfig reducedMotion="user">
      <motion.div
        layout
        className="relative"
        transition={{ layout: { duration: 0.2, ease: "easeOut" } }}
      >
        <motion.div
          initial={false}
          animate={{
            opacity: reviewsVisible ? 0 : 1,
            y: reviewsVisible ? -6 : 0,
          }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className={`min-w-0 ${reviewsVisible ? "pointer-events-none absolute inset-x-0 top-0" : "relative"}`}
          aria-hidden={reviewsVisible}
          inert={reviewsVisible}
        >
          {upload}
        </motion.div>
        <motion.div
          initial={false}
          animate={{
            opacity: reviewsVisible ? 1 : 0,
            y: reviewsVisible ? 0 : 6,
          }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className={`min-w-0 ${reviewsVisible ? "relative" : "pointer-events-none absolute inset-x-0 top-0"}`}
          aria-hidden={!reviewsVisible}
          inert={!reviewsVisible}
        >
          {reviews}
        </motion.div>
      </motion.div>
    </MotionConfig>
  );
}
