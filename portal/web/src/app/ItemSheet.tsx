import { AlertDialog, Button } from "@heroui/react";
import { useState } from "react";
import type { StepModel } from "../forms/steps";
import Sheet from "../shell/Sheet";
import { useApplication } from "./ApplicationStore";
import { RowsInLayout } from "./StepPane";

type Props = { step: StepModel; itemId: string; pageId: string | null; onPage: (pageId: string) => void; onClose: () => void };

// One building or addition, in a sheet: its pages with dots, Back and Next between them, Done
// to return to the list. Delete sits at the end, behind a confirmation, while more than the
// minimum remain.
export default function ItemSheet({ step, itemId, pageId, onPage, onClose }: Props) {
  const { removeItem, flush } = useApplication();
  const hub = step.hub!;
  const item = hub.items.find((i) => i.id === itemId);
  const rows = step.rows.filter((r) => r.itemId === itemId);
  const pages = hub.pages.filter((p) => rows.some((r) => r.field.page === p.id));
  const index = Math.max(0, pages.findIndex((p) => p.id === pageId));
  const page = pages[index];
  const [confirm, setConfirm] = useState(false);
  const noun = hub.kind === "building" ? "Building" : "Addition";
  const canDelete = hub.items.length > hub.repeat.min;

  async function done() {
    await flush();
    onClose();
  }

  return (
    <Sheet open title={item?.label ?? noun} onDone={() => void done()}
           pages={pages.map((p) => p.title)} pageIndex={index} onPage={(i) => onPage(pages[i].id)}>
      {page && <h2 className="text-[22px] font-bold">{page.title}</h2>}
      {page && <RowsInLayout rows={rows.filter((r) => r.field.page === page.id)} layout={page.layout} />}
      {index === pages.length - 1 && canDelete && (
        <div className="rounded-xl bg-[var(--app-row)]">
          <Button variant="ghost" fullWidth className="min-h-12 text-[var(--app-destructive)]" onPress={() => setConfirm(true)}
                  aria-label={`Delete ${item?.label ?? noun}`}>
            Delete {noun}
          </Button>
        </div>
      )}
      <AlertDialog.Backdrop isOpen={confirm} onOpenChange={setConfirm}>
        <AlertDialog.Container>
          <AlertDialog.Dialog>
            <AlertDialog.Header><AlertDialog.Heading>Delete {item?.label ?? noun}?</AlertDialog.Heading></AlertDialog.Header>
            <AlertDialog.Body>Its answers and files leave the application. This can't be undone here.</AlertDialog.Body>
            <AlertDialog.Footer>
              <Button variant="secondary" onPress={() => setConfirm(false)}>Cancel</Button>
              <Button variant="danger" onPress={async () => { setConfirm(false); if (await removeItem(itemId)) onClose(); }}>Delete</Button>
            </AlertDialog.Footer>
          </AlertDialog.Dialog>
        </AlertDialog.Container>
      </AlertDialog.Backdrop>
    </Sheet>
  );
}
