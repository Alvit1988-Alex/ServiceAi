"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { searchDialogs } from "@/app/api/dialogsApi";
import { ChannelType, DialogShort, DialogStatus } from "@/app/api/types";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { useBotsStore } from "@/store/bots.store";

import { SearchFilters } from "./components/SearchFilters/SearchFilters";
import { SearchResults } from "./components/SearchResults/SearchResults";
import styles from "./page.module.css";

interface FiltersState {
  query: string;
  status: DialogStatus | "";
  operatorId: string;
  channelType: ChannelType | "";
  page: number;
  perPage: number;
}

export default function SearchPage() {
  const router = useRouter();
  const { bots, selectedBotId, loadingBots, fetchBots, selectBot } = useBotsStore();

  const [filters, setFilters] = useState<FiltersState>({
    query: "",
    status: "",
    operatorId: "",
    channelType: "",
    page: 1,
    perPage: 10,
  });

  const [results, setResults] = useState<{
    items: DialogShort[];
    page: number;
    perPage: number;
    total: number;
    hasNext: boolean;
    error: string | null;
    loading: boolean;
  }>({
    items: [],
    page: 1,
    perPage: 10,
    total: 0,
    hasNext: false,
    error: null,
    loading: false,
  });

  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  useEffect(() => {
    if (!selectedBotId && bots.length > 0) {
      selectBot(bots[0].id);
    }
  }, [bots, selectedBotId, selectBot]);

  const currentBotId = useMemo(() => selectedBotId ?? bots[0]?.id ?? null, [selectedBotId, bots]);

  const handleFiltersChange = (values: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...values, page: values.page ?? prev.page }));
  };

  const resetToFirstPage = (values: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...values, page: 1 }));
  };

  const handleSearch = useCallback(async () => {
    if (!currentBotId) {
      return;
    }

    setResults((prev) => ({
      ...prev,
      page: filters.page,
      perPage: filters.perPage,
      loading: true,
      error: null,
    }));

    try {
      const response = await searchDialogs(currentBotId, {
        query: filters.query || undefined,
        status: filters.status || undefined,
        assigned_admin_id: filters.operatorId ? Number(filters.operatorId) : undefined,
        channel_type: filters.channelType || undefined,
        limit: filters.perPage,
        offset: (filters.page - 1) * filters.perPage,
      });

      setResults({
        items: response.items,
        page: response.page,
        perPage: response.per_page,
        total: response.total,
        hasNext: response.has_next,
        loading: false,
        error: null,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось выполнить поиск";
      setResults({
        items: [],
        page: filters.page,
        perPage: filters.perPage,
        total: 0,
        hasNext: false,
        loading: false,
        error: message,
      });
    }
  }, [currentBotId, filters]);

  useEffect(() => {
    void handleSearch();
  }, [handleSearch]);

  const handleRowClick = (dialog: DialogShort) => {
    router.push(`/bots/${dialog.bot_id}/dialogs/${dialog.id}`);
  };

  return (
    <AuthGuard>
      <LayoutShell
        title="Диалоги"
        description="Используйте фильтры, чтобы находить нужные диалоги среди всех ботов."
      >
        <div className={styles.container}>
          <section className={styles.section}>
            <div className={styles.titleRow}>
              <div className={styles.heading}>
                <h2 className={styles.title}>Фильтры поиска</h2>
                <p className={styles.description}>
                  Настройте параметры и выберите бота. Результаты обновятся автоматически после изменения фильтров.
                </p>
              </div>
            </div>

            <SearchFilters
              bots={bots}
              selectedBotId={currentBotId}
              loadingBots={loadingBots}
              filters={filters}
              onFiltersChange={(values) =>
                values.page
                  ? handleFiltersChange(values)
                  : resetToFirstPage(values as Partial<FiltersState>)
              }
              onBotChange={(botId) => {
                selectBot(botId);
                resetToFirstPage({});
              }}
              onSubmit={() => resetToFirstPage({})}
            />
          </section>

          <section className={styles.section}>
            <div className={styles.titleRow}>
              <div className={styles.heading}>
                <h2 className={styles.title}>Результаты</h2>
                <p className={styles.description}>Всего найдено: {results.total}</p>
              </div>
            </div>

            {!currentBotId && !loadingBots && (
              <p className={styles.statusMessage}>Выберите бота, чтобы начать поиск.</p>
            )}

            {currentBotId && (
              <SearchResults
                items={results.items}
                loading={results.loading}
                error={results.error}
                total={results.total}
                page={results.page}
                perPage={results.perPage}
                hasNext={results.hasNext}
                onRowClick={handleRowClick}
                onPageChange={(page) => handleFiltersChange({ page })}
                onPerPageChange={(perPage) => resetToFirstPage({ perPage })}
              />
            )}

            {results.error && <p className={styles.errorMessage}>{results.error}</p>}
          </section>
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
