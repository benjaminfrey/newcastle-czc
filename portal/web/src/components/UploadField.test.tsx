import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import * as apps from "../applications";
import UploadField from "./UploadField";

describe("UploadField", () => {
  it("shows each refusal in plain words", async () => {
    const onChange = vi.fn();
    for (const [reason, words] of [["infected", /virus check flagged/], ["too_large", /up to 25 MB/],
                                   ["unsupported_type", /PDF, JPEG, PNG or HEIC/], ["scanner_unavailable", /can't check files/]] as const) {
      vi.spyOn(apps, "uploadFile").mockResolvedValueOnce({ refused: reason });
      const { unmount } = render(<UploadField appId="a" fieldId="f" itemId={null} label="Add a sketch." attachments={[]} onChange={onChange} />);
      await userEvent.upload(screen.getByLabelText("Add a sketch."), new File(["x"], "plan.pdf", { type: "application/pdf" }));
      expect(await screen.findByRole("alert")).toHaveTextContent(words);
      unmount();
    }
    expect(onChange).not.toHaveBeenCalled();
  });

  it("lists an accepted file with a way to remove it", async () => {
    const onChange = vi.fn();
    vi.spyOn(apps, "uploadFile").mockResolvedValue({ id: "t1", field_id: "f", item_id: null, filename: "plan.pdf", content_type: "application/pdf", size_bytes: 2048 });
    render(<UploadField appId="a" fieldId="f" itemId={null} label="Add a sketch." attachments={[]} onChange={onChange} />);
    await userEvent.upload(screen.getByLabelText("Add a sketch."), new File(["x"], "plan.pdf", { type: "application/pdf" }));
    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ id: "t1", filename: "plan.pdf" })]);
  });
});
