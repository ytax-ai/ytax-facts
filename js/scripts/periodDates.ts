// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2026 TRIPLE J AI LLC
// Contains original tax-rule material from the ytax project.
// See the release-root LICENSING.md for scope and separate licensing options.

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const RELATIVE_PERIOD_DATE = /^TY(?:([+-]\d+))?-(\d{2})-(\d{2})$/;

export function dictionaryTaxYear(dictionaryRoot = process.env.YTAX_DICT_ROOT ?? '../../dictionary/ty2025'): number {
  const override = process.env.YTAX_TAX_YEAR;
  if (override && /^\d{4}$/.test(override)) return Number(override);
  const constantsXml = resolve(fileURLToPath(new URL('.', import.meta.url)), dictionaryRoot, 'constants.xml');
  const xml = readFileSync(constantsXml, 'utf8');
  const fact = /<Fact\s+path="\/taxYear"[^>]*>([\s\S]*?)<\/Fact>/.exec(xml)?.[1];
  const year = fact && /<Int>\s*(\d{4})\s*<\/Int>/.exec(fact)?.[1];
  if (!year) throw new Error(`${constantsXml}: /taxYear must have an integer <Int> value`);
  return Number(year);
}

export function resolvePeriodDates<T>(value: T, taxYear = dictionaryTaxYear()): T {
  if (Array.isArray(value)) return value.map((item) => resolvePeriodDates(item, taxYear)) as T;
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) out[key] = resolvePeriodDates(item, taxYear);
    return out as T;
  }
  if (typeof value !== 'string') return value;
  const match = RELATIVE_PERIOD_DATE.exec(value);
  if (!match) return value;
  const year = taxYear + Number(match[1] ?? 0);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
    throw new Error(`invalid tax-year-relative date ${JSON.stringify(value)}`);
  }
  return `${String(year).padStart(4, '0')}-${match[2]}-${match[3]}` as T;
}
