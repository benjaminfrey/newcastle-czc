import { Button, Label, ProgressBar } from "@heroui/react";
import { useId, useState } from "react";
import { removeAttachment, uploadFile, UPLOAD_MESSAGES, type Attachment } from "../applications";

type Props = {
  appId: string; fieldId: string; itemId: string | null; label: string;
  attachments: Attachment[]; onChange: (all: Attachment[]) => void;
};

const MAX_BYTES = 26_214_400;
const ACCEPT = ".pdf,.jpg,.jpeg,.png,.heic,.heif,application/pdf,image/jpeg,image/png,image/heic,image/heif";

function size(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Files go up one at a time as they're chosen; each is checked for viruses before the
// Town keeps it. Refusals are explained in plain words.
export default function UploadField({ appId, fieldId, itemId, label, attachments, onChange }: Props) {
  const inputId = useId();
  const [progress, setProgress] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const mine = attachments.filter((a) => a.field_id === fieldId && a.item_id === itemId);

  async function onFiles(files: FileList | null) {
    if (!files) return;
    let all = attachments;
    for (const file of Array.from(files)) {
      setMessage(null);
      // Checked here too, so nobody sends 26 MB over a phone connection only to be refused.
      if (file.size > MAX_BYTES) {
        setMessage(`${file.name}: ${UPLOAD_MESSAGES.too_large}`);
        break;
      }
      setProgress(0);
      const r = await uploadFile(appId, fieldId, itemId, file, setProgress);
      setProgress(null);
      if ("refused" in r) {
        setMessage(`${file.name}: ${UPLOAD_MESSAGES[r.refused] ?? UPLOAD_MESSAGES.unavailable}`);
        break;
      }
      all = [...all, { ...r, field_id: fieldId, item_id: itemId }];
      onChange(all);
    }
  }

  async function remove(a: Attachment) {
    if (await removeAttachment(a.id)) onChange(attachments.filter((x) => x.id !== a.id));
    else setMessage(UPLOAD_MESSAGES.unavailable);
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={inputId}>{label}</Label>
      <input id={inputId} type="file" multiple accept={ACCEPT} disabled={progress !== null}
             onChange={(e) => { void onFiles(e.target.files); e.target.value = ""; }} />
      {progress !== null && (
        <ProgressBar aria-label="Uploading" value={Math.round(progress * 100)}>
          <ProgressBar.Track><ProgressBar.Fill /></ProgressBar.Track>
        </ProgressBar>
      )}
      {message && <p role="alert">{message}</p>}
      {mine.length > 0 && (
        <ul className="flex flex-col gap-1" aria-label="Files added">
          {mine.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center gap-2">
              <a className="underline" href={`/api/attachments/${a.id}`}>{a.filename}</a>
              <span className="text-sm">({size(a.size_bytes)})</span>
              <Button variant="ghost" size="sm" onPress={() => void remove(a)} aria-label={`Remove ${a.filename}`}>Remove</Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
