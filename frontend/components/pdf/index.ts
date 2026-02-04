import dynamic from "next/dynamic";

// Export types for type safety
export type { PDFViewerModalProps, PDFPreviewProps } from "./PDFViewerModal";

// Dynamically import PDF components with SSR disabled
// react-pdf uses browser APIs that don't work during server-side rendering
export const PDFViewerModal = dynamic(
  () => import("./PDFViewerModal").then((mod) => mod.PDFViewerModal),
  { ssr: false }
);

export const PDFPreview = dynamic(
  () => import("./PDFViewerModal").then((mod) => mod.PDFPreview),
  { ssr: false }
);
