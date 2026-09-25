"use client";

import Alert from "@cloudscape-design/components/alert";
import Button from "@cloudscape-design/components/button";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { LoadingScreen } from "@/components/loading-screen";
import { Route53Shell } from "@/components/route53-shell";
import { useSession } from "@/hooks/use-session";
import { APIError } from "@/services/api";

export default function ProtectedRoute53Layout({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const session = useSession();
  const unauthorized =
    session.error instanceof APIError && session.error.status === 401;

  useEffect(() => {
    if (unauthorized) router.replace("/login");
  }, [router, unauthorized]);
  useEffect(() => {
    const redirectToLogin = () => router.replace("/login");
    window.addEventListener("session-unauthorized", redirectToLogin);
    return () =>
      window.removeEventListener("session-unauthorized", redirectToLogin);
  }, [router]);

  if (session.isPending || unauthorized) {
    return <LoadingScreen label="Checking your session" />;
  }
  if (session.error || !session.data) {
    return (
      <main>
        <Alert
          type="error"
          header="Unable to load your session"
          action={<Button onClick={() => session.refetch()}>Try again</Button>}
        >
          Confirm that the backend is running, then retry.
        </Alert>
      </main>
    );
  }
  return <Route53Shell user={session.data.user}>{children}</Route53Shell>;
}
