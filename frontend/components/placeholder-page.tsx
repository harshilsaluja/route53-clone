import Box from "@cloudscape-design/components/box";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <Container header={<Header variant="h1">{title}</Header>}>
      <Box color="text-body-secondary">
        This section is not implemented in this Route 53 clone.
      </Box>
    </Container>
  );
}
