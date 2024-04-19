<script setup>
import { RouterLink, RouterView } from "vue-router";
import appLogo from "./assets/opus-cleaner-logo.svg";
import euLogo from "./assets/eu.png";
import horizonLogo from "./assets/horizon-europe.png";
</script>

<template>
  <div class="navbar">
    <RouterLink v-bind:to="{ name: 'list-datasets' }"
      ><img class="logo" :src="appLogo" alt="opus cleaner logo"
    /></RouterLink>
  </div>
  <RouterView></RouterView>
  <div class="footer">
    <div class="thanking">
      <img :src="euLogo" alt="EU logo" class="eu-flag" />
      <p>
        This project has received funding from the European Union’s Horizon
        Europe research and innovation programme under grant agreement No
        101070350
      </p>
    </div>
    <div class="thanking right">
      <img :src="horizonLogo" alt="Horizon Europe logo" class="horizon-flag" />
      <p>
        The contents of this publication are the sole responsibility of the HPLT
        consortium and do not necessarily reflect the opinion of the European
        Union.
      </p>
    </div>
  </div>
</template>

<style>
@import "css/property-list.css";

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  margin: 20px 60px;
  font-family: "Lato", sans-serif;
  color: var(--main-copy);
}

.navbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 30px;
  align-items: center;
}
.logo {
  width: 180px;
}

.footer {
  display: flex;
  width: 90%;
  margin: 60px auto;
  font-family: "Lato", sans-serif;
}

.eu-flag,
.horizon-flag {
  width: 50px;
  height: auto;
  margin: 0 10px 0 0;
  flex: 0;
  align-self: flex-start;
}

.thanking {
  display: flex;
  font-weight: 300px;
  color: var(--secondary-copy);
  font-size: 14px;
  width: 45%;
}
.right {
  margin-left: 60px;
}

.icon-button {
  appearance: none;
  border: none;
  background: inherit;
  cursor: pointer;
  color: inherit;
}

.icon-button:visited {
  color: inherit;
}

.icon-button:disabled {
  cursor: inherit;
  opacity: 0.5; /* There should be a better way */
}
</style>
