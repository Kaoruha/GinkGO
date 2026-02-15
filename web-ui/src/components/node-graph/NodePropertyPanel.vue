<template>
  <div class="node-property-panel">
    <div class="panel-header">
      <h3>节点属性</h3>
      <a-button
        type="text"
        size="small"
        @click="$emit('close')"
      >
        <CloseOutlined />
      </a-button>
    </div>

    <div class="panel-content">
      <!-- Custom -->
      <div class="section">
        <div class="section-title">
          基本信息
        </div>
        <a-form-item label="节点名称">
          <a-input
            v-model:value="localNode.data.label"
            @change="handleUpdate"
          />
        </a-form-item>
        <a-form-item label="节点类型">
          <a-tag :color="getNodeTypeColor(node.type)">
            {{ NODE_TYPE_LABELS[node.type] }}
          </a-tag>
        </a-form-item>
      </div>

      <!-- Custom -->
      <div class="section">
        <div class="section-title">
          配置参数
        </div>

        <!-- ENGINE  -->
        <template v-if="node.type === NodeType.ENGINE">
</template>