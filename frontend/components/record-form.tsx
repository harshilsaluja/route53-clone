"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Container from "@cloudscape-design/components/container";
import Form from "@cloudscape-design/components/form";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import Select from "@cloudscape-design/components/select";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useState, type FormEvent } from "react";
import { APIError } from "@/services/api";
import type { DNSRecord, DNSRecordCreate, DNSRecordType } from "@/types/api";

const recordTypes: DNSRecordType[] = [
  "A", "AAAA", "CNAME", "TXT", "MX", "NS", "PTR", "SRV", "CAA",
];
const typeOptions = recordTypes.map((value) => ({ label: value, value }));
const tagOptions = ["issue", "issuewild", "iodef"].map((value) => ({
  label: value,
  value,
}));

interface ValueFields {
  primary: string;
  priority: string;
  weight: string;
  port: string;
  target: string;
  flags: string;
  tag: string;
}

function blankValue(): ValueFields {
  return {
    primary: "",
    priority: "",
    weight: "",
    port: "",
    target: "",
    flags: "0",
    tag: "issue",
  };
}

function parseValue(type: DNSRecordType, value: string): ValueFields {
  const fields = blankValue();
  if (type === "MX") {
    const [priority, ...target] = value.split(" ");
    return { ...fields, priority, target: target.join(" ") };
  }
  if (type === "SRV") {
    const [priority, weight, port, ...target] = value.split(" ");
    return { ...fields, priority, weight, port, target: target.join(" ") };
  }
  if (type === "CAA") {
    const match = value.match(/^(\d+)\s+(\S+)\s+(.+)$/);
    if (match) {
      let content = match[3];
      try {
        content = JSON.parse(content) as string;
      } catch {
        // Keep the stored text editable if it predates the current canonical form.
      }
      return { ...fields, flags: match[1], tag: match[2], primary: content };
    }
  }
  return { ...fields, primary: value };
}

function serializeValue(type: DNSRecordType, value: ValueFields): string {
  if (type === "MX") {
    return `${value.priority.trim()} ${value.target.trim()}`;
  }
  if (type === "SRV") {
    return [
      value.priority.trim(),
      value.weight.trim(),
      value.port.trim(),
      value.target.trim(),
    ].join(" ");
  }
  if (type === "CAA") {
    return `${value.flags.trim()} ${value.tag} ${JSON.stringify(value.primary)}`;
  }
  return type === "TXT" ? value.primary : value.primary.trim();
}

function valueLabel(type: DNSRecordType) {
  const labels: Record<DNSRecordType, string> = {
    A: "IPv4 address",
    AAAA: "IPv6 address",
    CNAME: "Value",
    TXT: "Value",
    MX: "Target",
    NS: "Nameserver",
    PTR: "Domain name / target",
    SRV: "Target",
    CAA: "Value",
  };
  return labels[type];
}

function valuePlaceholder(type: DNSRecordType) {
  const placeholders: Record<DNSRecordType, string> = {
    A: "192.0.2.10",
    AAAA: "2001:db8::1",
    CNAME: "target.example.com",
    TXT: "Text value",
    MX: "mail.example.com",
    NS: "ns1.example.net",
    PTR: "host.example.com",
    SRV: "service.example.com",
    CAA: "letsencrypt.org",
  };
  return placeholders[type];
}

export function RecordForm({
  zoneName,
  initial,
  mode,
  submitting,
  error,
  onSubmit,
  onCancel,
}: {
  zoneName: string;
  initial?: DNSRecord;
  mode: "create" | "edit";
  submitting: boolean;
  error: unknown;
  onSubmit: (payload: DNSRecordCreate) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [type, setType] = useState<DNSRecordType>(
    initial?.record_type ?? "A",
  );
  const [ttl, setTtl] = useState(String(initial?.ttl ?? 300));
  const [values, setValues] = useState<ValueFields[]>(
    initial?.values.map((value) => parseValue(initial.record_type, value)) ?? [
      blankValue(),
    ],
  );
  const [validationError, setValidationError] = useState<string>();
  const apiError = error instanceof APIError ? error.message : undefined;

  const updateValue = (
    index: number,
    field: keyof ValueFields,
    value: string,
  ) => {
    setValues((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    );
  };

  const changeType = (nextType: DNSRecordType) => {
    setType(nextType);
    setValues([blankValue()]);
    setValidationError(undefined);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const ttlNumber = Number(ttl);
    if (!Number.isInteger(ttlNumber) || ttlNumber <= 0) {
      setValidationError("TTL must be a positive whole number.");
      return;
    }
    if (type === "CNAME" && !name.trim()) {
      setValidationError("CNAME records cannot be created at the zone apex.");
      return;
    }
    const required = values.every((value) => {
      if (type === "MX") {
        return /^\d+$/.test(value.priority) && Boolean(value.target.trim());
      }
      if (type === "SRV") {
        return (
          /^\d+$/.test(value.priority) &&
          /^\d+$/.test(value.weight) &&
          /^\d+$/.test(value.port) &&
          Boolean(value.target.trim())
        );
      }
      if (type === "CAA") {
        return /^\d+$/.test(value.flags) && Boolean(value.primary);
      }
      return type === "TXT" ? value.primary.length > 0 : Boolean(value.primary.trim());
    });
    if (!values.length || !required) {
      setValidationError("Complete every value field before submitting.");
      return;
    }
    setValidationError(undefined);
    onSubmit({
      name: name.trim(),
      record_type: type,
      ttl: ttlNumber,
      routing_policy: "SIMPLE",
      values: values.map((value) => serializeValue(type, value)),
    });
  };

  return (
    <form onSubmit={submit}>
      <Form
        errorText={validationError ?? apiError}
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button formAction="none" onClick={onCancel} disabled={submitting}>
              Cancel
            </Button>
            <Button variant="primary" formAction="submit" loading={submitting}>
              {mode === "create" ? "Create record" : "Save changes"}
            </Button>
          </SpaceBetween>
        }
      >
        <SpaceBetween size="l">
          <Container header={<Header variant="h2">Record configuration</Header>}>
            <SpaceBetween size="l">
              <FormField
                label="Record name"
                description="Leave blank to create a record at the zone apex."
              >
                <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                  <Input
                    value={name}
                    placeholder="www"
                    onChange={({ detail }) => setName(detail.value)}
                    disabled={submitting}
                  />
                  <Box color="text-body-secondary">.{zoneName}</Box>
                </SpaceBetween>
              </FormField>
              <ColumnLayout columns={2}>
                <FormField label="Record type">
                  <Select
                    selectedOption={{ label: type, value: type }}
                    options={typeOptions}
                    onChange={({ detail }) =>
                      changeType(detail.selectedOption.value as DNSRecordType)
                    }
                    disabled={submitting}
                  />
                </FormField>
                <FormField label="TTL (seconds)">
                  <Input
                    type="number"
                    value={ttl}
                    onChange={({ detail }) => setTtl(detail.value)}
                    disabled={submitting}
                  />
                </FormField>
              </ColumnLayout>
              <FormField label="Routing policy">
                <Input value="Simple" disabled />
              </FormField>
              {type === "CNAME" && !name.trim() && (
                <Alert type="warning">
                  Enter a record name. CNAME records cannot be used at the zone apex.
                </Alert>
              )}
            </SpaceBetween>
          </Container>
          <Container
            header={
              <Header
                variant="h2"
                description="Values are saved as one logical record set."
                actions={
                  type !== "CNAME" ? (
                    <Button
                      onClick={() => setValues((current) => [...current, blankValue()])}
                      disabled={submitting}
                    >
                      Add another value
                    </Button>
                  ) : undefined
                }
              >
                Values
              </Header>
            }
          >
            <SpaceBetween size="l">
              {values.map((value, index) => (
                <div key={index}>
                  <SpaceBetween size="s">
                    <ColumnLayout
                      columns={type === "SRV" ? 4 : type === "MX" || type === "CAA" ? 3 : 1}
                    >
                      {type === "MX" && (
                        <FormField label="Priority">
                          <Input
                            type="number"
                            value={value.priority}
                            placeholder="10"
                            onChange={({ detail }) =>
                              updateValue(index, "priority", detail.value)
                            }
                          />
                        </FormField>
                      )}
                      {type === "SRV" && (
                        <>
                          <FormField label="Priority">
                            <Input
                              type="number"
                              value={value.priority}
                              placeholder="10"
                              onChange={({ detail }) =>
                                updateValue(index, "priority", detail.value)
                              }
                            />
                          </FormField>
                          <FormField label="Weight">
                            <Input
                              type="number"
                              value={value.weight}
                              placeholder="5"
                              onChange={({ detail }) =>
                                updateValue(index, "weight", detail.value)
                              }
                            />
                          </FormField>
                          <FormField label="Port">
                            <Input
                              type="number"
                              value={value.port}
                              placeholder="443"
                              onChange={({ detail }) =>
                                updateValue(index, "port", detail.value)
                              }
                            />
                          </FormField>
                        </>
                      )}
                      {type === "CAA" && (
                        <>
                          <FormField label="Flags">
                            <Input
                              type="number"
                              value={value.flags}
                              onChange={({ detail }) =>
                                updateValue(index, "flags", detail.value)
                              }
                            />
                          </FormField>
                          <FormField label="Tag">
                            <Select
                              selectedOption={{ label: value.tag, value: value.tag }}
                              options={tagOptions}
                              onChange={({ detail }) =>
                                updateValue(
                                  index,
                                  "tag",
                                  detail.selectedOption.value ?? "issue",
                                )
                              }
                            />
                          </FormField>
                        </>
                      )}
                      <FormField
                        label={
                          type === "MX" || type === "SRV"
                            ? "Target"
                            : type === "CAA"
                              ? "Value"
                              : valueLabel(type)
                        }
                      >
                        <Input
                          value={
                            type === "MX" || type === "SRV"
                              ? value.target
                              : value.primary
                          }
                          placeholder={
                            type === "MX"
                              ? "mail.example.com"
                              : type === "SRV"
                                ? "service.example.com"
                                : type === "CAA"
                                  ? "letsencrypt.org"
                                  : valuePlaceholder(type)
                          }
                          onChange={({ detail }) =>
                            updateValue(
                              index,
                              type === "MX" || type === "SRV" ? "target" : "primary",
                              detail.value,
                            )
                          }
                        />
                      </FormField>
                    </ColumnLayout>
                    {values.length > 1 && (
                      <Button
                        iconName="remove"
                        variant="inline-icon"
                        ariaLabel={`Remove value ${index + 1}`}
                        onClick={() =>
                          setValues((current) =>
                            current.filter((_, itemIndex) => itemIndex !== index),
                          )
                        }
                      />
                    )}
                  </SpaceBetween>
                </div>
              ))}
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Form>
    </form>
  );
}
