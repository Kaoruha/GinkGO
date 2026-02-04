import { ref } from 'vue'

const showCreateModal = ref(false)

export function useComponentList() {
  const openCreateModal = () => {
    showCreateModal.value = true
  }

  const closeCreateModal = () => {
    showCreateModal.value = false
  }

  return {
    showCreateModal,
    openCreateModal,
    closeCreateModal
  }
}
