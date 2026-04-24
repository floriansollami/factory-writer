import { Navigate, Route, Routes, useNavigate } from "react-router";

import { AdminHomePage } from "@/features/admin/AdminHomePage";
import { StyleGuideHomePage } from "@/features/style-guide/StyleGuideHomePage";
import { StyleGuideReviewPage } from "@/features/style-guide/StyleGuideReviewPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/admin" element={<AdminHomeRoute />} />
      <Route path="/style-guide" element={<StyleGuideHomeRoute />} />
      <Route path="/style-guide/review" element={<StyleGuideReviewRoute />} />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

function AdminHomeRoute() {
  const navigate = useNavigate();

  return <AdminHomePage onOpenStyleGuide={() => navigate("/style-guide")} />;
}

function StyleGuideHomeRoute() {
  const navigate = useNavigate();

  return (
    <StyleGuideHomePage
      onOpenAdminHome={() => navigate("/admin")}
      onOpenRulesReview={() => navigate("/style-guide/review")}
    />
  );
}

function StyleGuideReviewRoute() {
  const navigate = useNavigate();

  return (
    <StyleGuideReviewPage
      onBack={() => navigate("/style-guide")}
      onOpenAdminHome={() => navigate("/admin")}
    />
  );
}
