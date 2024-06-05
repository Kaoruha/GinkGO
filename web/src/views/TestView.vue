<template>
  <div>
    TEST
    <ConfirmDialog
      ref="dialog"
      @confirmMethod="tt"
      :title="'what the fuck'"
      :msg="'this is a message.'"
      :confirm_btn_text="'gogogo'"
    ></ConfirmDialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import DropDown from '../components/dropdown/DropDown.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const dialog = ref(null)

function tt() {
  console.log(1111111112222222)
}
</script>
