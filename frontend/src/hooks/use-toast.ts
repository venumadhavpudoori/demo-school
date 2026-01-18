import { toast as sonnerToast } from "sonner";

interface ToastOptions {
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Custom toast hook that wraps sonner's toast functionality
 * with consistent styling and behavior for the School ERP app.
 */
export function useToast() {
  const toast = {
    /**
     * Show a success toast notification
     */
    success: (message: string, options?: ToastOptions) => {
      sonnerToast.success(message, {
        description: options?.description,
        duration: options?.duration ?? 4000,
        action: options?.action
          ? {
              label: options.action.label,
              onClick: options.action.onClick,
            }
          : undefined,
      });
    },

    /**
     * Show an error toast notification
     */
    error: (message: string, options?: ToastOptions) => {
      sonnerToast.error(message, {
        description: options?.description,
        duration: options?.duration ?? 5000,
        action: options?.action
          ? {
              label: options.action.label,
              onClick: options.action.onClick,
            }
          : undefined,
      });
    },

    /**
     * Show a warning toast notification
     */
    warning: (message: string, options?: ToastOptions) => {
      sonnerToast.warning(message, {
        description: options?.description,
        duration: options?.duration ?? 4000,
        action: options?.action
          ? {
              label: options.action.label,
              onClick: options.action.onClick,
            }
          : undefined,
      });
    },

    /**
     * Show an info toast notification
     */
    info: (message: string, options?: ToastOptions) => {
      sonnerToast.info(message, {
        description: options?.description,
        duration: options?.duration ?? 4000,
        action: options?.action
          ? {
              label: options.action.label,
              onClick: options.action.onClick,
            }
          : undefined,
      });
    },

    /**
     * Show a loading toast notification that can be updated
     * Returns a function to dismiss the toast
     */
    loading: (message: string, options?: Omit<ToastOptions, "action">) => {
      const toastId = sonnerToast.loading(message, {
        description: options?.description,
        duration: options?.duration ?? Infinity,
      });

      return {
        dismiss: () => sonnerToast.dismiss(toastId),
        success: (successMessage: string, successOptions?: ToastOptions) => {
          sonnerToast.success(successMessage, {
            id: toastId,
            description: successOptions?.description,
            duration: successOptions?.duration ?? 4000,
          });
        },
        error: (errorMessage: string, errorOptions?: ToastOptions) => {
          sonnerToast.error(errorMessage, {
            id: toastId,
            description: errorOptions?.description,
            duration: errorOptions?.duration ?? 5000,
          });
        },
      };
    },

    /**
     * Show a promise-based toast that updates based on promise state
     */
    promise: <T,>(
      promise: Promise<T>,
      messages: {
        loading: string;
        success: string | ((data: T) => string);
        error: string | ((error: Error) => string);
      }
    ) => {
      return sonnerToast.promise(promise, {
        loading: messages.loading,
        success: messages.success,
        error: messages.error,
      });
    },

    /**
     * Dismiss a specific toast or all toasts
     */
    dismiss: (toastId?: string | number) => {
      sonnerToast.dismiss(toastId);
    },
  };

  return toast;
}

// Export a standalone toast object for use outside of React components
export const toast = {
  success: (message: string, options?: ToastOptions) => {
    sonnerToast.success(message, {
      description: options?.description,
      duration: options?.duration ?? 4000,
      action: options?.action
        ? {
            label: options.action.label,
            onClick: options.action.onClick,
          }
        : undefined,
    });
  },

  error: (message: string, options?: ToastOptions) => {
    sonnerToast.error(message, {
      description: options?.description,
      duration: options?.duration ?? 5000,
      action: options?.action
        ? {
            label: options.action.label,
            onClick: options.action.onClick,
          }
        : undefined,
    });
  },

  warning: (message: string, options?: ToastOptions) => {
    sonnerToast.warning(message, {
      description: options?.description,
      duration: options?.duration ?? 4000,
      action: options?.action
        ? {
            label: options.action.label,
            onClick: options.action.onClick,
          }
        : undefined,
    });
  },

  info: (message: string, options?: ToastOptions) => {
    sonnerToast.info(message, {
      description: options?.description,
      duration: options?.duration ?? 4000,
      action: options?.action
        ? {
            label: options.action.label,
            onClick: options.action.onClick,
          }
        : undefined,
    });
  },

  loading: (message: string, options?: Omit<ToastOptions, "action">) => {
    const toastId = sonnerToast.loading(message, {
      description: options?.description,
      duration: options?.duration ?? Infinity,
    });

    return {
      dismiss: () => sonnerToast.dismiss(toastId),
      success: (successMessage: string, successOptions?: ToastOptions) => {
        sonnerToast.success(successMessage, {
          id: toastId,
          description: successOptions?.description,
          duration: successOptions?.duration ?? 4000,
        });
      },
      error: (errorMessage: string, errorOptions?: ToastOptions) => {
        sonnerToast.error(errorMessage, {
          id: toastId,
          description: errorOptions?.description,
          duration: errorOptions?.duration ?? 5000,
        });
      },
    };
  },

  promise: <T,>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: Error) => string);
    }
  ) => {
    return sonnerToast.promise(promise, {
      loading: messages.loading,
      success: messages.success,
      error: messages.error,
    });
  },

  dismiss: (toastId?: string | number) => {
    sonnerToast.dismiss(toastId);
  },
};
