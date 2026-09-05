export const MAX_TABS_PER_PRINCIPAL = 8;

export async function enforceTabBudget(context, { preserve = [], maxTabs = MAX_TABS_PER_PRINCIPAL } = {}) {
  if (!Number.isInteger(maxTabs) || maxTabs < 1) throw new Error('E_TAB_BUDGET');
  const pages = context.pages().filter((page) => !page.isClosed());
  if (pages.length <= maxTabs) return { before: pages.length, after: pages.length, closed: 0 };

  const keep = [];
  for (const page of preserve) {
    if (page && !page.isClosed() && pages.includes(page) && !keep.includes(page) && keep.length < maxTabs) keep.push(page);
  }
  for (const page of [...pages].reverse()) {
    if (!keep.includes(page) && keep.length < maxTabs) keep.push(page);
  }
  const victims = pages.filter((page) => !keep.includes(page));
  for (const page of victims) await page.close({ runBeforeUnload: false }).catch(() => {});
  return { before: pages.length, after: context.pages().filter((page) => !page.isClosed()).length, closed: victims.length };
}
