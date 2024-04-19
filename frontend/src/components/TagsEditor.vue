<script setup>
import { ref } from "vue";
import { getCategoriesForDataset } from "../store/categories.js";
import { TagIcon, Edit3Icon } from "vue3-feather";
import CategoryPicker from "../components/CategoryPicker.vue";

const categoryPicker = ref();

const props = defineProps({
  dataset: Object,
});
</script>

<template>
  <div class="tags-container">
    <div class="category-tags">
      <span
        :class="category.name"
        v-for="category in getCategoriesForDataset(props.dataset)"
        :key="category.name"
      >
        <TagIcon width="20" strokeWidth="1" />
        <span class="tag-name">{{ category.name }}</span>
      </span>
    </div>
    <button
      class="icon-button"
      @click="categoryPicker.showForDataset(props.dataset, $event)"
      title="Change dataset tags"
    >
      <Edit3Icon />
    </button>
    <CategoryPicker ref="categoryPicker" />
  </div>
</template>

<style scoped>
.tags-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.category-tags {
  display: flex;
}

.medium,
.dirty,
.clean {
  display: flex;
  align-items: center;
  width: fit-content;
  padding: 3.5px 20px 3px 15px;
  border-radius: 15px;
  margin-right: 5px;
  font-size: 14px;
  background-color: #ddd;
  font-family: "Fira Code", monospace;
}
.tag-name {
  margin-left: 5px;
}
.clean {
  background-color: #afffca;
}

.dirty {
  background-color: #ffafaf;
}

.medium {
  background-color: #afcfff;
}
</style>
