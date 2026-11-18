import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat("vi-VN").format(num);
}

export function formatPercent(num: number): string {
  return `${(num * 100).toFixed(1)}%`;
}

export function formatScore(num: number): string {
  return num.toFixed(2);
}
