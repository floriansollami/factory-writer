import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router";

const AdminHomePage = lazy(() =>
  import("@/features/admin/AdminHomePage").then((module) => ({
    default: module.AdminHomePage,
  })),
);
const ProductSheetsHomePage = lazy(() =>
  import("@/features/product-sheets/ProductSheetsHomePage").then((module) => ({
    default: module.ProductSheetsHomePage,
  })),
);
const ProductSheetDetailPage = lazy(() =>
  import("@/features/product-sheets/ProductSheetDetailPage").then((module) => ({
    default: module.ProductSheetDetailPage,
  })),
);
const MarketingSignalsPage = lazy(() =>
  import("@/features/marketing-signals/MarketingSignalsPage").then((module) => ({
    default: module.MarketingSignalsPage,
  })),
);
const StyleGuideHomePage = lazy(() =>
  import("@/features/style-guide/StyleGuideHomePage").then((module) => ({
    default: module.StyleGuideHomePage,
  })),
);
const StyleGuideReviewPage = lazy(() =>
  import("@/features/style-guide/StyleGuideReviewPage").then((module) => ({
    default: module.StyleGuideReviewPage,
  })),
);

export function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<Navigate to="/admin" replace />} />
        <Route path="/admin" element={<AdminHomeRoute />} />
        <Route path="/marketing-signals" element={<MarketingSignalsRoute />} />
        <Route path="/product-sheets" element={<ProductSheetsHomeRoute />} />
        <Route path="/product-sheets/:productId" element={<ProductSheetDetailRoute />} />
        <Route path="/style-guide" element={<StyleGuideHomeRoute />} />
        <Route path="/style-guide/review" element={<StyleGuideReviewRoute />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </Suspense>
  );
}

function RouteFallback() {
  return (
    <main className="grid min-h-screen place-items-center bg-[var(--color-ivory)] text-sm font-semibold text-[var(--color-forest)]">
      Chargement…
    </main>
  );
}

function AdminHomeRoute() {
  const navigate = useNavigate();

  return (
    <AdminHomePage
      onOpenProductSheets={() => navigate("/product-sheets")}
      onOpenStyleGuide={() => navigate("/style-guide")}
    />
  );
}

function ProductSheetsHomeRoute() {
  const navigate = useNavigate();

  return (
    <ProductSheetsHomePage
      onOpenAdminHome={() => navigate("/admin")}
      onOpenMarketingSignals={(productId, returnTo) =>
        navigate(
          `/marketing-signals?productId=${encodeURIComponent(productId)}&returnTo=${encodeURIComponent(returnTo)}`,
        )
      }
      onOpenProductDetail={(productId) => navigate(`/product-sheets/${productId}`)}
      onOpenStyleGuide={(returnTo) =>
        navigate(
          returnTo === undefined
            ? "/style-guide"
            : `/style-guide?returnTo=${encodeURIComponent(returnTo)}`,
        )
      }
    />
  );
}

function MarketingSignalsRoute() {
  const navigate = useNavigate();

  return (
    <MarketingSignalsPage
      onOpenAdminHome={() => navigate("/admin")}
      onOpenProductSheets={() => navigate("/product-sheets")}
      onOpenStyleGuide={() => navigate("/style-guide")}
      onReturnTo={(returnTo) => navigate(returnTo)}
    />
  );
}

function ProductSheetDetailRoute() {
  const navigate = useNavigate();
  const { productId = "" } = useParams();

  return (
    <ProductSheetDetailPage
      onBack={() => navigate("/product-sheets")}
      onOpenAdminHome={() => navigate("/admin")}
      onOpenMarketingSignals={(targetProductId, returnTo) =>
        navigate(
          `/marketing-signals?productId=${encodeURIComponent(targetProductId)}&returnTo=${encodeURIComponent(returnTo)}`,
        )
      }
      onOpenProductSheets={() => navigate("/product-sheets")}
      onOpenStyleGuide={(returnTo) =>
        navigate(
          returnTo === undefined
            ? "/style-guide"
            : `/style-guide?returnTo=${encodeURIComponent(returnTo)}`,
        )
      }
      productId={productId}
    />
  );
}

function StyleGuideHomeRoute() {
  const navigate = useNavigate();

  return (
    <StyleGuideHomePage
      onOpenAdminHome={() => navigate("/admin")}
      onOpenProductSheets={() => navigate("/product-sheets")}
      onOpenRulesReview={(returnTo) =>
        navigate(
          returnTo === undefined
            ? "/style-guide/review"
            : `/style-guide/review?returnTo=${encodeURIComponent(returnTo)}`,
        )
      }
    />
  );
}

function StyleGuideReviewRoute() {
  const navigate = useNavigate();

  return (
    <StyleGuideReviewPage
      onBack={() => navigate("/style-guide")}
      onOpenAdminHome={() => navigate("/admin")}
      onOpenProductSheets={() => navigate("/product-sheets")}
    />
  );
}
