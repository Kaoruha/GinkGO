import { ref, computed } from 'vue'

const globalLoading = ref<Set<string>>(new Set())

export function useLoading() {
  const startLoading = (key: string = 'default') => {
    globalLoading.value.add(key)
  }

  const stopLoading = (key: string = 'default') => {
    globalLoading.value.delete(key)
  }

  const isLoading = (key: string = 'default') => {
    return computed(() => globalLoading.value.has(key))
  }

  const isAnyLoading = computed(() => globalLoading.value.size > 0)

  const withLoading = async <T>(key: string, fn: () => Promise<T>): Promise<T> => {
    startLoading(key)
    try {
      return await fn()
    } finally {
      stopLoading(key)
    }
  }

  return {
    startLoading,
    stopLoading,
    isLoading,
    isAnyLoading,
    withLoading,
  }
}
