<template>
  <div class="w-56 h-20 text-right">
    <Menu as="div" class="relative inline-block text-left">
      <MenuButton id="commissioning_canvas_menubtn"> </MenuButton>
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
              @click="$emit('rename')"
            >
              <MagnifyingGlassPlusIcon
                :active="active"
                class="mr-2 h-5 w-5 text-violet-400"
                aria-hidden="true"
              />
              Rename
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
              <PlusCircleIcon
                :active="active"
                class="mr-2 h-5 w-5 text-red-600"
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
  StarIcon,
  TrashIcon,
  MapIcon,
  MagnifyingGlassPlusIcon,
  MagnifyingGlassMinusIcon,
  DocumentArrowUpIcon,
  PlusCircleIcon,
  ArrowsPointingOutIcon
} from '@heroicons/vue/24/outline'

// Emits
const emit = defineEmits(['rename', 'delete'])

// Refs
const open = ref(true)
const menubtn = ref(null)

// Methods
function initMenuBTN() {
  menubtn.value = document.getElementById('commissioning_canvas_menubtn')
}

function simClick() {
  menubtn.value.dispatchEvent(new Event('click'))
}

// Lifecycle Hooks
onMounted(() => {
  initMenuBTN()
  simClick()
})

console.log('I am at setup in canvasdropdown.')
</script>
