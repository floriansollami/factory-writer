import { openDB, type DBSchema } from "idb";

type StoredStyleGuidePdf = {
  fileName: string;
  file: Blob;
  savedAt: string;
};

interface StyleGuidePdfDatabase extends DBSchema {
  pdfs: {
    key: string;
    value: StoredStyleGuidePdf;
  };
}

const DB_NAME = "factory-writer-style-guide-pdfs";
const STORE_NAME = "pdfs";

const dbPromise = openDB<StyleGuidePdfDatabase>(DB_NAME, 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains(STORE_NAME)) {
      db.createObjectStore(STORE_NAME, { keyPath: "fileName" });
    }
  },
});

export async function persistStyleGuidePdf(file: File): Promise<void> {
  const db = await dbPromise;
  await db.put(STORE_NAME, {
    fileName: file.name,
    file,
    savedAt: new Date().toISOString(),
  });
}

export async function loadStyleGuidePdf(fileName: string): Promise<Blob | null> {
  const db = await dbPromise;
  const record = await db.get(STORE_NAME, fileName);
  return record?.file ?? null;
}
