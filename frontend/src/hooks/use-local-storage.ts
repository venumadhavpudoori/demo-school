"use client";

import { useCallback, useSyncExternalStore } from "react";

function getServerSnapshot<T>(initialValue: T): T {
  return initialValue;
}

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  // Use useSyncExternalStore for proper hydration
  const getSnapshot = useCallback(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  }, [key, initialValue]);

  const subscribe = useCallback(
    (callback: () => void) => {
      const handleStorageChange = (e: StorageEvent) => {
        if (e.key === key) {
          callback();
        }
      };
      window.addEventListener("storage", handleStorageChange);
      return () => window.removeEventListener("storage", handleStorageChange);
    },
    [key]
  );

  const storedValue = useSyncExternalStore(
    subscribe,
    getSnapshot,
    () => getServerSnapshot(initialValue)
  );

  // Return a wrapped version of useState's setter function that persists to localStorage
  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        // Get current value from localStorage for function updates
        const currentValue = (() => {
          try {
            const item = window.localStorage.getItem(key);
            return item ? (JSON.parse(item) as T) : initialValue;
          } catch {
            return initialValue;
          }
        })();

        // Allow value to be a function so we have same API as useState
        const valueToStore = value instanceof Function ? value(currentValue) : value;
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
        // Dispatch storage event to trigger re-render
        window.dispatchEvent(new StorageEvent("storage", { key }));
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, initialValue]
  );

  return [storedValue, setValue];
}
