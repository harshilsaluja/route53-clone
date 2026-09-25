"use client";

import Alert from "@cloudscape-design/components/alert";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import Form from "@cloudscape-design/components/form";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import RadioGroup from "@cloudscape-design/components/radio-group";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Textarea from "@cloudscape-design/components/textarea";
import { useState, type FormEvent } from "react";
import { APIError } from "@/services/api";
import type { HostedZoneCreate, HostedZoneType } from "@/types/api";

interface ZoneFormProps {
  initial?: HostedZoneCreate;
  mode: "create" | "edit";
  submitting: boolean;
  error: unknown;
  onSubmit: (value: HostedZoneCreate) => void;
  onCancel: () => void;
}

function validateName(value: string): string | undefined {
  const name = value.trim().toLowerCase().replace(/\.$/, "");
  if (!name) return "Enter a domain name.";
  if (/\s/.test(name)) return "Domain names cannot contain spaces.";
  if (
    name.length > 253 ||
    name.split(".").some(
      (label) =>
        !label ||
        label.length > 63 ||
        !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i.test(label),
    )
  ) {
    return "Enter a valid domain name, such as example.com.";
  }
  return undefined;
}

export function ZoneForm({
  initial = { name: "", comment: null, type: "PUBLIC" },
  mode,
  submitting,
  error,
  onSubmit,
  onCancel,
}: ZoneFormProps) {
  const [name, setName] = useState(initial.name);
  const [comment, setComment] = useState(initial.comment ?? "");
  const [type, setType] = useState<HostedZoneType>(initial.type);
  const [nameError, setNameError] = useState<string>();
  const apiError = error instanceof APIError ? error : null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const validation = validateName(name);
    setNameError(validation);
    if (validation) return;
    onSubmit({
      name: name.trim(),
      comment: comment.trim() ? comment : null,
      type,
    });
  };

  return (
    <form onSubmit={submit}>
      <Form
        errorText={apiError?.message}
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button formAction="none" onClick={onCancel} disabled={submitting}>
              Cancel
            </Button>
            <Button variant="primary" formAction="submit" loading={submitting}>
              {mode === "create" ? "Create hosted zone" : "Save changes"}
            </Button>
          </SpaceBetween>
        }
      >
        <SpaceBetween size="l">
          {mode === "edit" && (
            <Alert type="warning" header="Changing the domain name">
              Relative record names stay unchanged, so their derived fully qualified
              domain names will change with the hosted zone name. Record target values
              are not rewritten.
            </Alert>
          )}
          <Container header={<Header variant="h2">Hosted zone configuration</Header>}>
            <SpaceBetween size="l">
              <FormField
                label="Domain name"
                description="Enter the DNS domain managed by this hosted zone."
                errorText={nameError}
              >
                <Input
                  value={name}
                  placeholder="example.com"
                  onChange={({ detail }) => {
                    setName(detail.value);
                    if (nameError) setNameError(undefined);
                  }}
                  disabled={submitting}
                />
              </FormField>
              <FormField
                label="Description"
                description="Optional. Add context for this hosted zone."
              >
                <Textarea
                  value={comment}
                  placeholder="Production domain"
                  onChange={({ detail }) => setComment(detail.value)}
                  disabled={submitting}
                />
              </FormField>
              <FormField label="Type">
                <RadioGroup
                  value={type}
                  onChange={({ detail }) =>
                    setType(detail.value as HostedZoneType)
                  }
                  items={[
                    {
                      value: "PUBLIC",
                      label: "Public hosted zone",
                      description: "Routes traffic on the public internet.",
                      disabled: submitting,
                    },
                    {
                      value: "PRIVATE",
                      label: "Private hosted zone",
                      description: "Represents private DNS within a VPC.",
                      disabled: submitting,
                    },
                  ]}
                />
              </FormField>
              {type === "PRIVATE" && (
                <Alert type="info">
                  VPC association is represented as mocked assignment data in this
                  clone. No real VPC integration is performed.
                </Alert>
              )}
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Form>
    </form>
  );
}
