import { Button, ProgressBar } from "@heroui/react";
import { useId, useState } from "react";
import { useProject } from "../app/ProjectStore";
import { removeAttachment, uploadFile, UPLOAD_MESSAGES, type Attachment } from "../projects";
import type { FormField } from "../projects";

const MAX_BYTES = 26_214_400;
// image/* lets a phone offer its camera as well as the photo library.
const ACCEPT = "application/pdf,image/*,.pdf,.jpg,.jpeg,.png,.heic,.heif";

function size(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// One button for a photo or a file; each is checked for viruses before the Town keeps it.
export default function UploadControl({ field, itemId }: { field: FormField; itemId: string | null }) {
  const store = useProject();
  const app = store.project!;
  const inputId = useId();
  const [progress, setProgress] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const mine = app.attachments.filter((a) => a.field_id === field.id && a.item_id === itemId);

  async function onFiles(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) {
      setMessage(null);
      if (file.size > MAX_BYTES) {
        setMessage(`${file.name}: ${UPLOAD_MESSAGES.too_large}`);
        break;
      }
      setProgress(0);
      const r = await uploadFile(app.id, field.id, itemId, file, setProgress);
      setProgress(null);
      if ("refused" in r) {
        setMessage(`${file.name}: ${UPLOAD_MESSAGES[r.refused] ?? UPLOAD_MESSAGES.unavailable}`);
        break;
      }
      store.attachmentAdded({ ...r, field_id: field.id, item_id: itemId });
    }
  }

  async function remove(a: Attachment) {
    if (await removeAttachment(a.id)) store.attachmentRemoved(a.id);
    else setMessage(UPLOAD_MESSAGES.unavailable);
  }

  return (
    <div className="flex flex-col gap-3">
      <label htmlFor={inputId}
             className="flex min-h-14 cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-[var(--app-separator)] bg-[var(--app-row)] px-4 text-[17px] font-semibold text-[var(--app-accent-text)] focus-within:ring-2 focus-within:ring-[var(--app-accent-text)]">
        Take a photo or choose a file
        <input id={inputId} type="file" aria-label={`Take a photo or choose a file: ${field.label ?? field.official_label}`} multiple accept={ACCEPT} className="sr-only" disabled={progress !== null}
               onChange={(e) => { void onFiles(e.target.files); e.target.value = ""; }} />
      </label>
      <p className="text-[15px] text-[var(--app-secondary-label)]">PDF, JPEG, PNG or HEIC · up to 25 MB</p>
      {progress !== null && (
        <ProgressBar aria-label="Uploading" value={Math.round(progress * 100)}>
          <ProgressBar.Track><ProgressBar.Fill /></ProgressBar.Track>
        </ProgressBar>
      )}
      {message && <p role="alert" className="text-[var(--app-destructive)]">{message}</p>}
      {mine.length > 0 && (
        <ul className="flex flex-col divide-y divide-[var(--app-separator)] rounded-xl bg-[var(--app-row)]" aria-label="Files added">
          {mine.map((a) => (
            <li key={a.id} className="flex min-h-12 items-center gap-3 px-4">
              {a.content_type.startsWith("image/") && a.content_type !== "image/heic"
                ? <img src={`/api/attachments/${a.id}`} alt="" className="size-10 rounded object-cover" />
                : <span aria-hidden="true" className="flex size-10 items-center justify-center rounded bg-[var(--app-ground)] text-[13px]">PDF</span>}
              <a className="flex-1 truncate underline" href={`/api/attachments/${a.id}`}>{a.filename}</a>
              <span className="text-[13px] text-[var(--app-secondary-label)]">{size(a.size_bytes)}</span>
              <Button variant="ghost" className="min-h-11 text-[var(--app-destructive)]" onPress={() => void remove(a)}
                      aria-label={`Remove ${a.filename}`}>Remove</Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
