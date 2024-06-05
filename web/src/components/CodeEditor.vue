<template>
  <div class="w-screen h-[calc(100vh-80px)]">
    <Codemirror
      v-model="model"
      :style="{ height: '100%' }"
      :extensions="extensions"
      :autofocus="true"
      :disabled="false"
      @ready="handleClick('ready', $event)"
      @change="handleClick('change', $event)"
      @focus="handleClick('focus', $event)"
      @blur="handleClick('blur', $event)"
    />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
const extensions = [python()]
const handleClick = (type, val) => {
  // console.log(type, val);
}

// 定义 code 作为响应式数据
// const code = ref("print('Hello World!')");

function save_to_remote() {
  console.log('Pretend save to remote.')
}

// 新增一个方法来处理输入事件，并更新 code 的值
// const updateCode = (newValue) => {
// code.value = newValue;
// };

const model = defineModel()

// defineExpose ({ updateCode })
</script>
