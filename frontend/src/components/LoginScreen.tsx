"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, loginAccount, registerAccount } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import { Mds01Logo } from "./Mds01Logo";

/** Render the small local account boundary for the research workspace. */
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
      const message = submissionError instanceof ApiError
        ? submissionError.message
        : "The workspace could not be reached. Check that the backend is running.";
      setError(message);
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
    <div className="flex min-h-screen items-center justify-center px-5 py-12 sm:px-8">
      <div className="w-full max-w-md">
        <div className="flex justify-center">
          <Mds01Logo />
        </div>
        <div className="mt-10 rounded-xl border border-rule bg-surface p-6 shadow-sm sm:p-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-teal-dark">Private workspace</p>
            <h1 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-ink">
              {registering ? "Create your account" : "Sign in to MDS01"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-ink-muted">
              Your EEG analyses and video privacy jobs are visible only to your account.
            </p>
          </div>

          <form className="mt-7 space-y-5" onSubmit={(event) => void submit(event)}>
            <div>
              <label className="text-sm font-semibold text-ink" htmlFor="login-email">Email address</label>
              <input
                className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3 text-sm text-ink outline-none transition focus:border-teal focus:ring-4 focus:ring-teal/15"
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
                <label className="text-sm font-semibold text-ink" htmlFor="login-password">Password</label>
                {registering && <span className="text-xs text-ink-faint">12 characters minimum</span>}
              </div>
              <input
                className="mt-2 h-11 w-full rounded-lg border border-input bg-background px-3 text-sm text-ink outline-none transition focus:border-teal focus:ring-4 focus:ring-teal/15"
                id="login-password"
                name="password"
                type="password"
                autoComplete={registering ? "new-password" : "current-password"}
                minLength={registering ? 12 : undefined}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            {error && (
              <div className="flex items-start gap-2.5 rounded-lg border border-red/30 bg-red-soft px-3.5 py-3 text-sm leading-5 text-red" role="alert">
                <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <Button className="w-full" size="lg" type="submit" disabled={submitting}>
              {submitting ? <Icon name="spinner" className="size-4 animate-spin" /> : <Icon name="lock" className="size-4" />}
              {submitting ? "Working…" : registering ? "Create account" : "Sign in"}
            </Button>
          </form>

          <div className="mt-6 border-t border-rule pt-5 text-center text-sm text-ink-muted">
            <span>{registering ? "Already have an account?" : "New to this workspace?"}</span>{" "}
            <button className="font-semibold text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-teal" type="button" onClick={switchMode}>
              {registering ? "Sign in" : "Create an account"}
            </button>
          </div>
        </div>
        <p className="mt-5 text-center text-xs leading-5 text-ink-faint">
          Local prototype accounts are not email-verified. MDS01 is for research review only.
        </p>
      </div>
    </div>
  );
}
