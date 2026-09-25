"use client";

import Alert from "@cloudscape-design/components/alert";
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
      <div className="login-brand">
        <strong>AWS</strong> Route 53 Clone
      </div>
      <Container
        header={
          <Header variant="h1" description="Sign in to manage hosted zones">
            Sign in
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
            <SpaceBetween size="l">
              <Alert type="info" header="Demo account">
                Email: demo@route53clone.dev<br />
                Password: Scaler@123
              </Alert>
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
            </SpaceBetween>
          </Form>
        </form>
      </Container>
    </main>
  );
}
