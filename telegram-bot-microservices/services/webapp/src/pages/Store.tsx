import { useTranslation } from "react-i18next";
import { StoreLayout } from "../components/store/StoreLayout";

export function Store() {
  const { t } = useTranslation();
  return <StoreLayout title={t("store_title")} showBack />;
}
