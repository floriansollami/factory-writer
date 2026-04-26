import { openDB, type DBSchema } from "idb";

type StoredTechnicalSourcePdf = {
  sourceId: string;
  productId: string;
  fileName: string;
  file: Blob;
  savedAt: string;
};

interface TechnicalSourcePdfDatabase extends DBSchema {
  pdfs: {
    key: string;
    value: StoredTechnicalSourcePdf;
    indexes: {
      by_file_name: string;
    };
  };
}

const DB_NAME = "factory-writer-technical-source-pdfs";
const STORE_NAME = "pdfs";

const dbPromise = openDB<TechnicalSourcePdfDatabase>(DB_NAME, 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains(STORE_NAME)) {
      const store = db.createObjectStore(STORE_NAME, { keyPath: "sourceId" });
      store.createIndex("by_file_name", "fileName");
    }
  },
});

export async function persistTechnicalSourcePdf({
  file,
  fileName,
  productId,
  sourceId,
}: {
  file: File;
  fileName: string;
  productId: string;
  sourceId: string;
}): Promise<void> {
  const db = await dbPromise;
  await db.put(STORE_NAME, {
    sourceId,
    productId,
    fileName,
    file,
    savedAt: new Date().toISOString(),
  });
}

export async function loadTechnicalSourcePdf(sourceId: string): Promise<Blob | null> {
  const db = await dbPromise;
  const record = await db.get(STORE_NAME, sourceId);
  return record?.file ?? null;
}

export async function loadTechnicalSourcePdfByFileName(
  fileName: string,
): Promise<Blob | null> {
  const db = await dbPromise;
  const record = await db.getFromIndex(STORE_NAME, "by_file_name", fileName);
  return record?.file ?? null;
}
