<script setup>
// Docs for Vue@3: https://vuejs.org/guide/introduction.html
// Docs for draggable@4: https://github.com/SortableJS/vue.draggable.next
import {
  ref,
  computed,
  watch,
  watchEffect,
  onMounted,
  onUnmounted,
  readonly,
} from "vue";
import draggable from "vuedraggable";
import { stream } from "../stream.js";
import { getFilters, filterRequiresLanguage } from "../store/filters.js";
import { getFilterSteps, defaultValue } from "../store/filtersteps.js";
import { formatNumberSuffix } from "../format.js";
import Checkbox from "../components/Checkbox.vue";
import SegmentedControl from "../components/SegmentedControl.vue";
import FilterStep from "../components/FilterStep.vue";
import FilterOutputTable from "../components/FilterOutputTable.vue";
import {
  Edit3Icon,
  TagIcon,
  PlusIcon,
  MinusIcon,
  RotateCcwIcon,
  RotateCwIcon,
} from "vue3-feather";
import { getUniqueId } from "../hacks.js";
import VueSelect from "vue-select";
import "vue-select/dist/vue-select.css";

const multiDragKey = navigator.platform.match(/^(Mac|iPhone$)/)
  ? "Meta"
  : "Control";

const SampleStep = Symbol("SampleStep");

const FETCH_SAMPLE_DELAY = 1000;

const { dataset } = defineProps({
  dataset: Object,
});

const displayAsRows = ref(false);

const displayWhitespace = ref(false);

const VIEWS = ["original", "clean", "changes"];

const view = ref("clean"); // one of VIEWs

const isFetchingSamples = ref(false);

const languages = computed(() => {
  // Unloaded state the dataset will have a name, but not all its details yet
  return (dataset?.columns || []).map(({ lang }) => lang);
});

const filters = computed(() => {
  let filters = getFilters().value || [];
  // monolingual data? Only show monolingual filters
  if (languages.value?.length === 1)
    filters = filters.filter((def) => def.type === "monolingual");
  return filters;
});

const filterSteps = getFilterSteps(dataset);

/**
 * {
 *   {
 *     "stdout": Object[],
 *     "stderr": String,
 *     "returncode": Number
 *   }[]
 * }
 */
const samples = ref([]);

const sample = computed(() => {
  return samples.value.length > 0
    ? samples.value[samples.value.length - 1]
    : null;
});

const original = computed(() => {
  return samples.value.length > 0 ? samples.value[0] : null;
});

async function fetchSample(dataset, steps, { signal }) {
  isFetchingSamples.value = true;
  samples.value = [];

  try {
    const response = stream(
      `/api/datasets/${encodeURIComponent(dataset.name)}/sample`,
      {
        method: "POST",
        signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(steps, null, 2),
      }
    );

    for await (let sample of response) {
      if (!signal.aborted) samples.value.push(readonly(sample));
    }
  } catch (err) {
    if (
      err.toString().indexOf("The operation was aborted") === -1 &&
      err.toString().indexOf("The user aborted a request") === -1
    )
      throw err;
  } finally {
    isFetchingSamples.value = false;
  }
}

// Fetch sample once, and every time any of the related variables change
// which is either filterSteps or the dataset. Explicitly not watching `samples`
// as that changes async thanks to this and would cause issues.
watch(
  [filterSteps.steps, dataset],
  (val, prev, onCleanup) => {
    const fetch = () => {
      const abortController = new AbortController();
      onCleanup(() => abortController.abort());
      fetchSample(dataset, filterSteps.steps.value, abortController);
    };

    // First time we fetch, we fetch without delay. In all other cases, we delay
    // to "batch" multiple changes when someone is editing the filters. An
    // essential side effect of this is that the first time the watcher is run
    // the dependencies are correctly tracked since they don't occur inside a
    // async callback (all dependencies are touched before the first `await`).
    if (samples.value.length === 0) {
      fetch();
    } else {
      const timeout = setTimeout(fetch, FETCH_SAMPLE_DELAY);
      onCleanup(() => clearTimeout(timeout));
    }
  },
  {
    immediate: true, // Run on initialisation as well
  }
);

function createFilterStep(filter) {
  return {
    id: getUniqueId(),
    filter: filter.name,
    language: filterRequiresLanguage({ filter: filter.name })
      ? languages.value[0]
      : null,
    parameters: Object.fromEntries(
      Object.entries(filter.parameters).map(([key, parameter]) => [
        key,
        defaultValue(parameter),
      ])
    ),
  };
}

function addFilterStep(filter) {
  const step = createFilterStep(filter);
  filterSteps.update([...filterSteps.steps.value, step]);

  // Open new steps by default
  filterIsOpen.get(step).value = true;
}

function removeFilterStep(i) {
  filterSteps.update([
    ...filterSteps.steps.value.slice(0, i),
    ...filterSteps.steps.value.slice(i + 1),
  ]);
}

function updateFilterStep(i, step) {
  filterSteps.update([
    ...filterSteps.steps.value.slice(0, i),
    step,
    ...filterSteps.steps.value.slice(i + 1),
  ]);
}

function setFilterData(dataTransfer, el) {
  dataTransfer.setData(
    "text/plain",
    JSON.stringify(createFilterStep(el.__draggable_context.element), null, 2)
  );
}

function setFilterStepData(dataTransfer, el) {
  dataTransfer.setData(
    "text/plain",
    JSON.stringify(el.__draggable_context.element, null, 2)
  );
}

function getLoadingStage(index) {
  if (samples.value.length < index + 1)
    // `+1` because first of samples is the raw sample)
    return "pending";
  else if (samples.value.length === index + 1) return "loading";
  else if (samples.value[index + 1].returncode === 0) return "loaded";
  else return "failed";
}

function filterFilters(filters, query) {
  return query.length === 0
    ? filters
    : filters.filter(({ name, description }) => {
        return (
          name.toLowerCase().indexOf(query.toLowerCase()) !== -1 ||
          (description &&
            description.toLowerCase().indexOf(query.toLowerCase()) !== -1)
        );
      });
}

const categoryPicker = ref();

const lineCounts = computed(() => {
  return {
    original: samples.value.length > 0 ? samples.value[0].stdout?.length : null,
    clean:
      samples.value.length === filterSteps.steps.value.length + 1
        ? samples.value[filterSteps.steps.value.length].stdout?.length
        : null,
    changes: null /* too expensive to compute on the fly anyway */,
  };
});

// Listens for ctrl+z (undo) and ctrl+shift+z (redo)
function keyListener(e) {
  if ((multiDragKey === "Meta" ? e.metaKey : e.ctrlKey) && e.keyCode === 90) {
    if (e.shiftKey) {
      if (filterSteps.canRedo.value) filterSteps.redo();
    } else {
      if (filterSteps.canUndo.value) filterSteps.undo();
    }
    e.preventDefault();
  }
}

onMounted(() => {
  document.body.addEventListener("keydown", keyListener);
});

onUnmounted(() => {
  document.body.removeEventListener("keydown", keyListener);
});

const filterIsOpen = new (class {
  constructor() {
    this.map = new Map();
  }

  get(filterStep) {
    if (!this.map.has(filterStep.id)) this.map.set(filterStep.id, ref(false));
    return this.map.get(filterStep.id);
  }
})();
</script>

<template>
  <div class="clean-corpus-container">
    <div class="output-panel">
      <header class="controls">
        <Checkbox v-model="displayAsRows" class="rows"
          >Display as rows</Checkbox
        >

        <Checkbox v-model="displayWhitespace" class="whitespace"
          >Display whitespace</Checkbox
        >

        <div class="button-group">
          <button
            class="icon-button"
            title="Undo"
            @click="filterSteps.undo()"
            :disabled="!filterSteps.canUndo.value"
          >
            <RotateCcwIcon />
          </button>
          <button
            class="icon-button"
            title="Redo"
            @click="filterSteps.redo()"
            :disabled="!filterSteps.canRedo.value"
          >
            <RotateCwIcon />
          </button>
        </div>

        <SegmentedControl class="table-buttons" v-model="view" :options="VIEWS">
          <template v-slot="{ option }">
            {{ option }}
            <small
              class="line-count"
              title="Number of lines in sample"
              v-if="lineCounts[option] !== null"
              >{{ lineCounts[option] }}</small
            >
          </template>
        </SegmentedControl>
      </header>

      <div class="filter-output">
        <FilterOutputTable
          class="filter-output-table"
          :languages="languages"
          :rows="view === 'original' ? original?.stdout : sample?.stdout"
          :ref-rows="view === 'changes' ? original?.stdout : null"
          :display-as-rows="displayAsRows"
          :display-whitespace="displayWhitespace"
        />
        <div class="filter-error" v-if="sample?.stderr" translate="no">
          <pre>{{ sample.stderr }}</pre>
        </div>
      </div>
    </div>

    <div class="filter-container">
      <div class="filter-input">
        <VueSelect
          :filter="filterFilters"
          :options="filters"
          label="name"
          placeholder="Search filters…"
          v-on:option:selected="addFilterStep"
        >
          <template #option="{ name, description }">
            <div class="filter-search-result" :title="description">
              {{ name }}<br />
              <small>{{ description }}</small>
            </div>
          </template>
        </VueSelect>
      </div>

      <draggable
        tag="ol"
        class="filter-steps"
        item-key="id"
        v-bind:modelValue="filterSteps.steps.value"
        v-on:update:modelValue="filterSteps.update($event)"
        :group="{ name: 'filters' }"
        :multi-drag="true"
        :set-data="setFilterStepData"
        :multi-drag-key="multiDragKey"
      >
        <template v-slot:item="{ element: filterStep, index: i }">
          <FilterStep
            class="filter-step"
            v-bind:languages="languages"
            v-bind:modelValue="filterStep"
            v-on:update:modelValue="updateFilterStep(i, $event)"
            v-bind:open="filterIsOpen.get(filterStep).value"
            v-on:update:open="filterIsOpen.get(filterStep).value = $event"
          >
            <template v-slot:header>
              <span class="filter-name">{{ filterStep.filter }}</span>
              <small
                v-if="getLoadingStage(i) === 'loaded'"
                class="line-count"
                title="Line count"
                >{{ samples[i + 1]?.stdout?.length }}</small
              >
              <small
                v-else
                class="loading-state"
                :class="{ [getLoadingStage(i)]: true }"
                >{{ getLoadingStage(i) }}</small
              >
              <button
                v-on:click="removeFilterStep(i)"
                class="icon-button remove-filter-btn"
                title="Do not use filter"
              >
                <MinusIcon />
              </button>
            </template>
          </FilterStep>
        </template>
      </draggable>
      <draggable
        tag="ul"
        class="available-filters"
        v-model="filters"
        item-key="name"
        v-bind:group="{ name: 'filters', pull: 'clone', put: false }"
        v-bind:sort="false"
        v-bind:set-data="setFilterData"
        v-bind:clone="createFilterStep"
      >
        <template v-slot:item="{ element: filter }">
          <li class="filter">
            <details class="property-list">
              <summary>
                <span v-bind:title="filter.description" class="filter-name">{{
                  filter.name
                }}</span>
                <button
                  v-on:click="addFilterStep(filter)"
                  class="icon-button add-filter-btn"
                  title="Use filter"
                >
                  <PlusIcon />
                </button>
              </summary>
              <p>{{ filter.description }}</p>
            </details>
          </li>
        </template>
      </draggable>
    </div>
  </div>
</template>

<style scoped>
@import "../css/property-list.css";
.clean-corpus-container {
  flex: 1 1 auto;
  overflow: hidden;
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
}

.output-panel {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 4px 0px 4px 0; /* 16px to align with the diff gutter */
}

.filter-output {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  overflow: hidden;
}

.filter-output-table {
  flex: 1;
}

.filter-error {
  border-top: 1px solid var(--border-color);
  flex: 0 0 auto;
  overflow: hidden;
  overflow-y: auto;
  max-height: 100%;
  height: 40%;
  resize: vertical;
}

.filter-error pre {
  white-space: pre-wrap;
}

.filter-container {
  overflow: auto; /*temporary! */
  flex: 0 1 300px;
  overflow: auto;
  border-left: 1px solid var(--border-color);
  margin: 3.7px 0 0 7px;
}

.filter-input {
  background: #17223d;
  color: white;
  padding: 0.4em;
}

.filter-input .v-select {
  background: Canvas; /* TODO messes with the rounded corners */
  color: CanvasText;
  --vs-border-radius: 0;
  --vs-border-color: #e4960e;
  --vs-border-width: 2px; /* TODO looks wonky */
}

.filter-input .v-select .filter-search-result {
  overflow: hidden;
  text-overflow: ellipsis;
}

.filter-steps {
  flex: 1 0 auto;
  overflow-y: auto;
}

.filters.display-separately {
  flex-direction: row-reverse;
  flex: 0 0 600px;
  overflow: hidden;
  border: 0;
}

.filters.display-separately .available-filters,
.filters.display-separately .filter-steps {
  flex: 0 0 50%;
  overflow: hidden;
  overflow-y: auto;
  box-sizing: border-box;
  border: 0;
  border-left: 1px solid var(--border-color);
}

.filter {
  display: flex;
}

.filter > details {
  display: flex;
  flex: 1;
}

.filter > details > summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter .filter-name {
  flex: 2;
  text-overflow: ellipsis;
  overflow: hidden;
}

.filter .filter-type {
  flex: 1;
  font-size: 0.8em;
  padding-left: 0.5em;
}

.add-filter-btn,
.remove-filter-btn {
  flex: 0;
  align-self: center;
}

.available-filters li,
.filter-steps li {
  border: 1px solid #313640;
  position: relative; /* for ::after arrow */
  background: var(--background-color); /* for when it is being dragged */
}

.loading-state,
.line-count {
  flex: 0 !important;
}

.loading-state.failed {
  color: red;
}

.filter-steps .filter-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.available-filters,
.filter-steps {
  margin: 0;
  padding: 0;
  list-style: none;
}

.dataset-categories {
  display: inline;
  list-style: none;
  padding: 0;
}

.dataset-categories li {
  display: inline;
}

.table-buttons .line-count::before {
  content: "(";
}

.table-buttons .line-count::after {
  content: ")";
}
.whitespace,
.rows {
  font-size: 16px;
}
</style>
