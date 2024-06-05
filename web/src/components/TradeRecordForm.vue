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
                <div :class="blk_cls" class="z-20 relative">
                  <div>Code</div>
                  <CodeGroup v-model="record.code"></CodeGroup>
                </div>
                <div :class="blk_cls" class="z-10 relative">
                  <div>Direction</div>
                  <DirectionGroup v-model="record.direction"></DirectionGroup>
                </div>
                <div :class="blk_cls" class="z-0 relative">
                  <div>Date</div>
                  <input
                    type="text"
                    :class="input_cls"
                    placeholder="Date ..."
                    v-model="record.date"
                  />
                </div>
                <div :class="blk_cls">
                  <div>Price</div>
                  <input
                    type="text"
                    :class="input_cls"
                    placeholder="Price ..."
                    v-model="record.price"
                  />
                </div>
                <div :class="blk_cls">
                  <div>Volume</div>
                  <input
                    type="text"
                    :class="input_cls"
                    placeholder="Volume ..."
                    v-model="record.volume"
                  />
                </div>
                <div :class="blk_cls">
                  <div>Comission</div>
                  <input
                    type="text"
                    :class="input_cls"
                    placeholder="Comission ..."
                    v-model="record.comission"
                  />
                </div>
                <div :class="blk_cls">
                  <div>Fee</div>
                  <input
                    type="text"
                    :class="input_cls"
                    placeholder="Fee ..."
                    v-model="record.fee"
                  />
                </div>
              </div>

              <div class="mt-4">
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                  @click="callConfirmMethod"
                >
                  Submit
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
import { ref, watch, onMounted } from 'vue'
import CodeGroup from '../components/CodeGroup.vue'
import DirectionGroup from '../components/DirectionGroup.vue'
import { TransitionRoot, TransitionChild, Dialog, DialogPanel, DialogTitle } from '@headlessui/vue'

const title = ref('Add Trade Record')
const msg = ref('Add Trade Record')

const blk_cls = 'h-[80px]'

const input_cls = 'border px-2 py-2 w-80 rounded-lg flex-grow'

const record = defineModel()

const record_id = ref(null)
const code = ref(null)
const direction = ref(null)
const date = ref(null)
const price = ref(null)
watch(price, (newValue, oldValue) => {
  console.log('price update')
  // console.log("price update", newValue)
})
const volume = ref(null)
const comission = ref(null)
const fee = ref(null)
watch(code, (newValue, oldValue) => {
  // console.log('code update ', newValue)
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
