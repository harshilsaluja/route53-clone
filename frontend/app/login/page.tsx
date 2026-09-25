"use client";

import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import Form from "@cloudscape-design/components/form";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession } from "@/hooks/use-session";
import { APIError } from "@/services/api";
import { login } from "@/services/auth";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const session = useSession();
  const [email, setEmail] = useState("demo@route53clone.dev");
  const [password, setPassword] = useState("Scaler@123");
  const mutation = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(["session"], data);
      router.replace("/route53/hosted-zones");
    },
  });

  useEffect(() => {
    if (session.data) router.replace("/route53/hosted-zones");
  }, [router, session.data]);

  const message =
    mutation.error instanceof APIError
      ? mutation.error.status === 401
        ? "The email or password is incorrect."
        : mutation.error.message
      : null;

  return (
    <main className="login-page">
      <header className="login-header"><div className="login-aws-wordmark">aws<span /></div></header>
      <div className="login-card">
        <Container
          header={
            <Header
              variant="h1"
              description="Use the assignment demo account to continue to the console."
            >
              Sign in to AWS
            </Header>
          }
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            <Form
              errorText={message ?? undefined}
              actions={
                <Button
                  variant="primary"
                  formAction="submit"
                  loading={mutation.isPending}
                  disabled={!email || !password}
                >
                  Sign in
                </Button>
              }
            >
              <SpaceBetween size="m">
                <FormField label="Email">
                  <Input
                    type="email"
                    value={email}
                    onChange={({ detail }) => setEmail(detail.value)}
                    disabled={mutation.isPending}
                  />
                </FormField>
                <FormField label="Password">
                  <Input
                    type="password"
                    value={password}
                    onChange={({ detail }) => setPassword(detail.value)}
                    disabled={mutation.isPending}
                  />
                </FormField>
                <div className="login-demo-account">
                  <strong>Demo account</strong>
                  <div><span>Email</span><code>demo@route53clone.dev</code></div>
                  <div><span>Password</span><code>Scaler@123</code></div>
                  <small>Route 53 Clone · Demo environment</small>
                </div>
              </SpaceBetween>
            </Form>
          </form>
        </Container>
      </div>
    </main>
  );
}
