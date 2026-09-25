import Box from "@cloudscape-design/components/box";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <SpaceBetween size="m">
      <Header
        variant="h1"
        description="AWS Route 53 management and configuration."
      >
        {title}
      </Header>
      <Container header={<Header variant="h2">{title} overview</Header>}>
        <Box color="text-body-secondary">
          This section is not implemented in this Route 53 clone.
        </Box>
      </Container>
    </SpaceBetween>
  );
}
