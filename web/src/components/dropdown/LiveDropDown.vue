<template>
  <div class="w-56 h-0 text-right" @contextmenu="preventDefault">
    <Menu as="div" class="relative inline-block text-left">
      <MenuButton id="file_dropdown_menubtn"> </MenuButton>
      <MenuItems
        class="absolute right-0 mt-2 w-56 origin-top-right divide-y divide-gray-100 rounded-md bg-white shadow-lg ring-1 ring-black/5 focus:outline-none"
      >
        <div class="px-1 py-1">
          <MenuItem v-slot="{ active }">
            <button
              :class="[
                active ? 'bg-violet-500 text-white' : 'text-gray-900',
                'group flex w-full items-center rounded-md px-2 py-2 text-sm'
              ]"
              @click="$emit('detail')"
            >
              <DocumentTextIcon
                :active="active"
                :class="active ? 'text-white' : 'text-violet-400'"
                class="mr-2 h-5 w-5"
                aria-hidden="true"
              />
              Detail
            </button>
          </MenuItem>
        </div>
        <div class="px-1 py-1">
          <MenuItem v-slot="{ active }">
            <button
              :class="[
                active ? 'bg-violet-500 text-white' : 'text-gray-900',
                'group flex w-full items-center rounded-md px-2 py-2 text-sm'
              ]"
              @click="$emit('start')"
            >
              <PlayCircleIcon
                :active="active"
                :class="active ? 'text-white' : 'text-violet-400'"
                class="mr-2 h-5 w-5"
                aria-hidden="true"
              />
              Start
            </button>
          </MenuItem>
          <MenuItem v-slot="{ active }">
            <button
              :class="[
                active ? 'bg-violet-500 text-white' : 'text-gray-900',
                'group flex w-full items-center rounded-md px-2 py-2 text-sm'
              ]"
              @click="$emit('pause')"
            >
              <PauseCircleIcon
                :active="active"
                :class="active ? 'text-white' : 'text-violet-400'"
                class="mr-2 h-5 w-5"
                aria-hidden="true"
              />
              Pause
            </button>
          </MenuItem>
          <MenuItem v-slot="{ active }">
            <button
              :class="[
                active ? 'bg-violet-500 text-white' : 'text-gray-900',
                'group flex w-full items-center rounded-md px-2 py-2 text-sm'
              ]"
              @click="$emit('stop')"
            >
              <StopCircleIcon
                :active="active"
                :class="active ? 'text-white' : 'text-violet-400'"
                class="mr-2 h-5 w-5"
                aria-hidden="true"
              />
              Stop
            </button>
          </MenuItem>
          <MenuItem v-slot="{ active }">
            <button
              :class="[
                active ? 'bg-violet-500 text-white' : 'text-gray-900',
                'group flex w-full items-center rounded-md px-2 py-2 text-sm'
              ]"
              @click="$emit('restart')"
            >
              <ArrowPathRoundedSquareIcon
                :active="active"
                :class="active ? 'text-white' : 'text-violet-400'"
                class="mr-2 h-5 w-5"
                aria-hidden="true"
              />
              Restart
            </button>
          </MenuItem>
        </div>
        <div class="px-1 py-1">
          <MenuItem v-slot="{ active }">
            <button
              :class="[
                active ? 'bg-red-500 text-white' : 'text-red-600',
                'group flex w-full items-center rounded-md px-2 py-2 text-sm'
              ]"
              @click="$emit('delete')"
            >
              <TrashIcon
                :active="active"
                :class="active ? 'text-white' : 'text-red-600'"
                class="mr-2 h-5 w-5"
                aria-hidden="true"
              />
              Delete
            </button>
          </MenuItem>
        </div>
      </MenuItems>
    </Menu>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue'
import {
  PencilSquareIcon,
  TrashIcon,
  ClipboardDocumentListIcon,
  PlayCircleIcon,
  PauseCircleIcon,
  StopCircleIcon,
  ArrowPathRoundedSquareIcon,
  DocumentTextIcon
} from '@heroicons/vue/24/outline'

// Emits
const emit = defineEmits(['detail', 'copy', 'start', 'pause', 'stop', 'restart', 'delete'])

// Refs
const menubtn = ref(null)

// Methods
function initMenuBTN() {
  menubtn.value = document.getElementById('file_dropdown_menubtn')
}

function simClick() {
  menubtn.value.dispatchEvent(new Event('click'))
}

// Lifecycle Hooks
onMounted(() => {
  initMenuBTN()
})

function preventDefault(event) {
  event.preventDefault()
}

defineExpose({ simClick })
</script>
