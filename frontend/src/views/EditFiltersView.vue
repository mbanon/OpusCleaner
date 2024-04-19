<script setup>
import { useRoute } from "vue-router";
import { ref, computed } from "vue";
import { getDataset } from "../store/datasets.js";
import { UploadIcon } from "vue3-feather";
import TagsEditor from "../components/TagsEditor.vue";
import FilterEditor from "../components/FilterEditor.vue";

const route = useRoute();

const dataset = computed(() => {
  return getDataset(route.params.datasetName);
});
</script>

<template>
  <div class="filter-editor">
    <header>
      <h2 class="dataset-name">
        Dataset: <em>{{ dataset.name }}</em>
      </h2>
      <TagsEditor :dataset="dataset" />
    </header>

    <FilterEditor v-if="dataset" :dataset="dataset" />

    <Teleport to=".navbar">
      <RouterLink
        class="import-data-button"
        v-bind:to="{ name: 'add-dataset' }"
      >
        Import dataset
        <UploadIcon class="import-data-icon" width="20" />
      </RouterLink>
    </Teleport>
  </div>
</template>

<style scoped>
@import "../css/navbar.css";

.filter-editor {
  overflow: hidden;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}
.dataset-name {
  margin-bottom: 15px;
  font-size: 30px;
}
.import-data-button {
  display: flex;
  align-items: center;
  border: none;
  border-radius: 3px;
  height: 40px;
  padding: 0 30px;
  background-color: #17223d;
  color: #efefef;
  font-size: 16px;
  text-decoration: none;
}
</style>
