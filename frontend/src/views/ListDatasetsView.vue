<script setup>
import { ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { getDatasets } from "../store/datasets.js";
import { getFilterSteps } from "../store/filtersteps.js";
import { getCategoriesForDataset } from "../store/categories.js";
import TagsEditor from "../components/TagsEditor.vue";
import {
  UploadIcon,
  CodeIcon,
  FilterIcon,
  PieChartIcon,
  Edit3Icon,
  TagIcon,
} from "vue3-feather";
import NoDatasetImage from "../assets/data-cuate.svg";

function languages(dataset) {
  const intl = new Intl.DisplayNames([], { type: "language" });
  return (dataset?.columns || []).map(({ lang }) => {
    try {
      return intl.of(lang.replace("_", "-"));
    } catch (e) {
      return lang;
    }
  });
}
</script>

<template>
  <div class="table-container-first-screen">
    <Teleport to=".navbar">
      <RouterLink
        class="import-data-button"
        v-bind:to="{ name: 'add-dataset' }"
      >
        Import dataset
        <UploadIcon class="import-data-icon" width="20" />
      </RouterLink>
    </Teleport>

    <h2 class="table-title">Your datasets</h2>
    <div class="table-container" v-if="getDatasets().length > 0">
      <table class="datasets-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Languages</th>
            <th>Categories</th>
            <th>Filter steps</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="dataset in getDatasets()" :key="dataset.id">
            <td>{{ dataset.name }}</td>
            <td>{{ languages(dataset).join("–") }}</td>
            <td class="tags"><TagsEditor :dataset="dataset" /></td>
            <td class="filter-steps">
              {{ getFilterSteps(dataset).steps.value.length }}
            </td>
            <td class="actions">
              <RouterLink
                class="icon-button"
                title="Show filter yaml"
                :to="{
                  name: 'edit-filters-yaml',
                  params: {
                    datasetName: dataset.name,
                    format: 'configuration-for-opusfilter.yaml',
                  },
                }"
                ><CodeIcon
              /></RouterLink>
              <RouterLink
                class="icon-button"
                title="Edit filters"
                :to="{
                  name: 'edit-filters',
                  params: { datasetName: dataset.name },
                }"
                ><FilterIcon
              /></RouterLink>
              <RouterLink
                class="icon-button"
                title="Show dataset statistics"
                :to="{}"
                ><PieChartIcon
              /></RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="illustration-container" v-else>
      <img :src="NoDatasetImage" />
      <p>
        No datasets yet. Click on the import data button on the right to get
        started.
      </p>
      <p class="credits">
        Image by
        <a
          href="https://www.freepik.com/free-vector/no-data-concept-illustration_8961448.htm"
          target="_blank"
          >storyset on Freepik</a
        >.
      </p>
    </div>
    <RouterView /><!-- for modals -->
  </div>
</template>

<style scoped>
.table-title {
  margin-bottom: 5px;
}
.table-container {
  min-height: 60vh;
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
  font-size: 18px;
  text-decoration: none;
}

.import-data-icon {
  margin-left: 10px;
}
.datasets-table {
  border: 1px solid #1c3948;
  border-collapse: collapse;
  width: 100%;
}

.datasets-table thead {
  background-color: #17223d;
  color: #efefef;
  font-size: 16px;
  text-align: left;
  font-weight: 300;
}

.datasets-table tbody {
  color: var(--tertiary-copy);
}

.datasets-table thead th {
  padding: 20px 0px 10px 10px;
  min-width: 150px;
}

.datasets-table tbody tr {
  border-bottom: 1px solid var(--table-border);
  border-right: 1px solid var(--table-border);
}

.datasets-table tbody td {
  border-right: 1px solid var(--table-border);
}

.datasets-table tbody tr td {
  padding: 10px;
}

.category-tags {
  display: flex;
}

.tags {
  width: 40%;
}
.actions {
  display: flex;
  justify-content: space-around;
}
.filter-steps {
  text-align: right;
}

.illustration-container {
  text-align: center;
  font-size: 1.2em;
  line-height: 2;
}

.illustration-container img {
  max-width: 600px;
  width: calc(100% - 4em);
  margin: 2em;
}

.illustration-container .credits {
  font-size: 0.8em;
}
</style>
