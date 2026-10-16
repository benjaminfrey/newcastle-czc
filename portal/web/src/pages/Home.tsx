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
        <Link to="/start" className="underline">Do I need a permit?</Link>
        <Link to="/where" className="underline">Look up a property</Link>
        <Link to="/signin" className="underline">Sign in</Link>
      </Card.Content>
    </Card>
  );
}
