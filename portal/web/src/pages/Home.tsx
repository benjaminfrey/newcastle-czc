import { Card } from "@heroui/react";
import { Link } from "react-router";

export default function Home() {
  return (
    <Card>
      <Card.Header>
        <Card.Title>Planning a project in Newcastle?</Card.Title>
        <Card.Description>
          Answer a few simple questions to find out which permit you need, then apply online.
        </Card.Description>
      </Card.Header>
      <Card.Content className="flex flex-col gap-2">
        <p>This site is being built. You can already try the first step.</p>
        <Link to="/where" className="underline">Start: where is your project?</Link>
        <Link to="/signin" className="underline">Sign in</Link>
      </Card.Content>
    </Card>
  );
}
