<template>
  <TransitionRoot appear :show="isOpen" as="template" @contextmenu="preventDefault">
    <Dialog as="div" @close="closeModal" class="relative z-10">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black/25" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <TransitionChild
            as="template"
            enter="duration-300 ease-out"
            enter-from="opacity-0 scale-95"
            enter-to="opacity-100 scale-100"
            leave="duration-200 ease-in"
            leave-from="opacity-100 scale-100"
            leave-to="opacity-0 scale-95"
          >
            <DialogPanel
              class="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all"
            >
              <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900">
                {{ title }}
              </DialogTitle>
              <div class="mt-2">
                <p class="text-sm text-gray-500">
                  {{ msg }}
                </p>
                <input
                  v-if="show_input"
                  type="text"
                  class="mt-4 border px-2 py-2 w-80 rounded-lg flex-grow"
                  placeholder="Portfolio name ..."
                  v-model="portfolio_name"
                  @keyup.enter="callConfirmMethod"
                />
              </div>

              <div class="mt-4">
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                  @click="callConfirmMethod"
                >
                  {{ confirm_btn_text }}
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup>
import { ref } from 'vue'
import { TransitionRoot, TransitionChild, Dialog, DialogPanel, DialogTitle } from '@headlessui/vue'

const portfolio_name = defineModel()

const props = defineProps({
  title: {
    type: String,
    default: 'Payment successful test'
  },
  msg: {
    type: String,
    default:
      ' Your payment has been successfully submitted. We’ve sent you an email with all of the details of your order. '
  },
  confirm_btn_text: {
    type: String,
    default: 'Got it, thanks a lot!'
  },
  show_input: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirmMethod'])

function defaultConfirmMethod() {
  closeModal()
}

function callConfirmMethod() {
  if (!emit('confirmMethod')) {
    defaultConfirmMethod()
  }
}

const isOpen = ref(false)

function closeModal() {
  isOpen.value = false
}

function openModal() {
  isOpen.value = true
}

function preventDefault(event) {
  event.preventDefault()
}

defineExpose({ openModal })
</script>
