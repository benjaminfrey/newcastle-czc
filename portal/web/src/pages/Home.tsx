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
      <Card.Content>
        <p>This part of the site is being built. You can already sign in to try it.</p>
        <Link to="/signin" className="underline">Sign in</Link>
      </Card.Content>
    </Card>
  );
}
