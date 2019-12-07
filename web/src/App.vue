<template>
  <v-app dark>
    <v-navigation-drawer
      v-model="drawer"
      :clipped="clipped"
      :mini-variant="miniVariant"
      persistent
      enable-resize-watcher
      fixed
      app
    >
      <v-list>
        <v-list-tile
          v-for="item in items"
          :key="item.icon"
          value="true"
        >
          <v-list-tile-action>
            <v-icon v-html="item.icon" />
          </v-list-tile-action>
          <v-list-tile-content>
            <v-list-tile-title v-text="item.title" />
          </v-list-tile-content>
        </v-list-tile>
      </v-list>
    </v-navigation-drawer>
    <v-toolbar
      :clipped-left="clipped"
      app
    >
      <v-toolbar-side-icon @click.stop="drawer = !drawer" />
      <v-btn
        icon
        @click.stop="miniVariant = !miniVariant"
      >
        <v-icon v-html="miniVariant ? 'chevron_right' : 'chevron_left'" />
      </v-btn>
      <v-btn
        icon
        @click.stop="clipped = !clipped"
      >
        <v-icon>web</v-icon>
      </v-btn>
      <v-btn
        icon
        @click.stop="fixed = !fixed"
      >
        <v-icon>remove</v-icon>
      </v-btn>
      <v-toolbar-title v-text="title" />
      <v-spacer />
    </v-toolbar>
    <v-content>
      <router-view />
    </v-content>
    <v-footer
      :fixed="fixed"
      app
    >
      <span>Picnic Technologies</span>
      <v-spacer />
      <v-btn
        :href="auth_url"
        round
        color="primary"
        dark
      >
        <v-icon left>
          fab fa-github
        </v-icon>
        Sign-in through Github
      </v-btn>
    </v-footer>
  </v-app>
</template>

<script>
  export default {
    name: 'App',
    data () {
      return {
        clipped: false,
        drawer: false,
        fixed: false,
        items: [],
        miniVariant: false,
        title: 'Hall of Fame',
        auth_url: 'https://github.com/login/oauth/authorize?scope=user:email&client_id=github_client_id&redirect_uri=https://localhost:9999/api/authenticate'
      };
    }
  };
</script>
