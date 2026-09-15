"use client";

import { FormEvent, useState } from "react";
import { motion, MotionConfig } from "motion/react";
import { useRouter } from "next/navigation";
import { ApiError, loginAccount, registerAccount } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import { Mds01Logo } from "./Mds01Logo";

/** Render the local account boundary with a compact preview of the product flow. */
export function LoginScreen() {
  const router = useRouter();
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (registering) await registerAccount(email, password);
      else await loginAccount(email, password);
      router.replace("/dashboard");
    } catch (submissionError) {
      setError(
        submissionError instanceof ApiError
          ? submissionError.message
          : "The workspace could not be reached. Check that the backend is running.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode() {
    setRegistering((current) => !current);
    setError(null);
    setPassword("");
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="login-shell px-5 py-6 sm:px-8 sm:py-10">
        <motion.main
          className="login-layout"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <section className="login-form-column">
            <Mds01Logo />
            <div className="mt-16 max-w-md sm:mt-24">
              <p className="eyebrow">Private research workspace</p>
              <motion.div
                key={registering ? "register" : "login"}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25 }}
              >
                <h1 className="mt-3 text-[clamp(2rem,5vw,2.8rem)] font-semibold leading-[1.04] tracking-[-0.055em] text-ink">
                  {registering ? "Create your account" : "Sign in to MDS01"}
                </h1>
                <p className="mt-4 max-w-sm text-[0.96rem] leading-7 text-ink-muted">
                  Your EEG analyses and video review jobs stay scoped to your
                  account.
                </p>
              </motion.div>

              <form
                className="mt-9 space-y-5"
                onSubmit={(event) => void submit(event)}
              >
                <div>
                  <label
                    className="text-sm font-semibold text-ink"
                    htmlFor="login-email"
                  >
                    Email address
                  </label>
                  <input
                    className="mt-2 h-12 w-full rounded-xl border border-input bg-background px-3.5 text-sm text-ink outline-none transition focus:border-teal focus:ring-4 focus:ring-teal/15"
                    id="login-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <label
                      className="text-sm font-semibold text-ink"
                      htmlFor="login-password"
                    >
                      Password
                    </label>
                    {registering && (
                      <span className="text-xs text-ink-faint">
                        12 characters minimum
                      </span>
                    )}
                  </div>
                  <input
                    className="mt-2 h-12 w-full rounded-xl border border-input bg-background px-3.5 text-sm text-ink outline-none transition focus:border-teal focus:ring-4 focus:ring-teal/15"
                    id="login-password"
                    name="password"
                    type="password"
                    autoComplete={
                      registering ? "new-password" : "current-password"
                    }
                    minLength={registering ? 12 : undefined}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                </div>
                {error && (
                  <div
                    className="flex items-start gap-2.5 rounded-xl border border-red/30 bg-red-soft px-3.5 py-3 text-sm leading-5 text-red"
                    role="alert"
                  >
                    <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}
                <Button
                  className="h-12 w-full rounded-xl"
                  size="lg"
                  type="submit"
                  disabled={submitting}
                >
                  {submitting ? (
                    <Icon name="spinner" className="size-4 animate-spin" />
                  ) : (
                    <Icon name="lock" className="size-4" />
                  )}
                  {submitting
                    ? "Working…"
                    : registering
                      ? "Create account"
                      : "Sign in"}
                </Button>
              </form>

              <p className="mt-6 text-sm text-ink-muted">
                {registering
                  ? "Already have an account?"
                  : "New to this workspace?"}{" "}
                <button
                  className="font-semibold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal"
                  type="button"
                  onClick={switchMode}
                >
                  {registering ? "Sign in" : "Create an account"}
                </button>
              </p>
            </div>
            <p className="mt-14 text-xs leading-5 text-ink-faint">
              Local prototype accounts are not email-verified. MDS01 is for
              research review only.
            </p>
          </section>

          <motion.aside
            className="login-preview"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.12, duration: 0.5 }}
            aria-label="MDS01 workflow preview"
          >
            <div className="login-preview-glow" aria-hidden="true" />
            <div className="relative z-10 flex h-full flex-col justify-between p-7 sm:p-10">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="eyebrow text-teal-dark">MDS01 / workflow</p>
                  <h2 className="mt-3 max-w-xs text-2xl font-semibold leading-tight tracking-[-0.04em] text-ink">
                    One workspace for protected review.
                  </h2>
                </div>
                <span className="grid size-11 place-items-center rounded-2xl bg-white/75 text-teal shadow-sm">
                  <Icon name="shield" className="size-6" weight="bold" />
                </span>
              </div>
              <WorkflowDiagram />
              <div className="rounded-2xl border border-white/80 bg-white/60 p-4 backdrop-blur">
                <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-faint">
                  Built for review
                </p>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  Privacy treatment is shown before model output. Scores remain
                  research evidence, not a diagnosis.
                </p>
              </div>
            </div>
          </motion.aside>
        </motion.main>
      </div>
    </MotionConfig>
  );
}

function WorkflowDiagram() {
  return (
    <motion.div
      className="workflow-diagram relative mt-10 flex flex-1 items-center justify-center py-8"
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: { delayChildren: 0.15, staggerChildren: 0.1 },
        },
      }}
    >
      <div className="workflow-nodes relative grid w-full max-w-[38rem] grid-cols-4 gap-3">
        <motion.div
          className="workflow-connector absolute left-[8%] right-[8%] top-10 h-px bg-gradient-to-r from-teal/10 via-teal/70 to-teal/10"
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{
            delay: 0.1,
            duration: 0.7,
            ease: [0.22, 1, 0.36, 1],
          }}
          aria-hidden="true"
        />
        <WorkflowNode
          icon="upload"
          title="Upload"
          detail="EEG, video, or both"
        />
        <WorkflowNode
          icon="lock"
          title="Privacy"
          detail="Protected before model input"
        />
        <WorkflowNode
          icon="activity"
          title="Model"
          detail="Window scores and intervals"
        />
        <WorkflowNode
          icon="check"
          title="Review"
          detail="Evidence in context"
        />
      </div>
    </motion.div>
  );
}

function WorkflowNode({
  icon,
  title,
  detail,
}: {
  icon: "upload" | "lock" | "activity" | "check";
  title: string;
  detail: string;
}) {
  return (
    <motion.div
      className="workflow-node relative flex min-w-0 flex-col items-center gap-3 text-center"
      variants={{
        hidden: { opacity: 0, y: 12 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
        },
      }}
    >
      <motion.span
        className="relative z-10 grid size-14 shrink-0 place-items-center rounded-2xl border border-white/90 bg-white/85 text-teal shadow-sm backdrop-blur"
        whileHover={{ y: -3, scale: 1.04 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        <Icon name={icon} className="size-6" weight="bold" />
      </motion.span>
      <div className="min-w-0">
        <p className="text-sm font-bold text-ink">{title}</p>
        <p className="mt-1 text-xs leading-5 text-ink-muted">{detail}</p>
      </div>
    </motion.div>
  );
}
