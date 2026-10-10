import { describe, expect, it } from "vitest";
import { MAX_BYTES, getDoc, listDocs, removeDoc, saveDoc } from "./docs.js";

const file = (name, text = "hello") => new File([text], name, { type: "application/pdf" });

describe("documents store", () => {
  it("saves, reads and removes a file", async () => {
    await saveDoc("a@x.com", "app1", "resume", file("cv.pdf"));
    const doc = await getDoc("a@x.com", "app1", "resume");
    expect(doc.name).toBe("cv.pdf");
    expect(doc.size).toBe(5);
    await removeDoc("a@x.com", "app1", "resume");
    expect(await getDoc("a@x.com", "app1", "resume")).toBeUndefined();
  });

  it("keeps users and applications apart", async () => {
    await saveDoc("a@x.com", "app1", "resume", file("a.pdf"));
    await saveDoc("a@x.com", "app2", "cover", file("b.pdf"));
    await saveDoc("b@x.com", "app1", "resume", file("c.pdf"));
    expect(await listDocs("a@x.com")).toEqual({ app1: ["resume"], app2: ["cover"] });
    expect(await listDocs("b@x.com")).toEqual({ app1: ["resume"] });
    expect(await listDocs("nobody@x.com")).toEqual({});
  });

  it("replaces a file saved twice in the same slot", async () => {
    await saveDoc("c@x.com", "app9", "cover", file("old.pdf"));
    await saveDoc("c@x.com", "app9", "cover", file("new.pdf"));
    expect((await getDoc("c@x.com", "app9", "cover")).name).toBe("new.pdf");
  });

  it("limits files to 5 MB", () => {
    expect(MAX_BYTES).toBe(5 * 1024 * 1024);
  });
});
