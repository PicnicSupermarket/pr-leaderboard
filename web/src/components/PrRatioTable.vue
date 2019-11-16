<template>
  <v-container fluid>
    <v-layout v-bind="layout_direction">
      <v-flex xs3>
        <template v-for="description in descriptions" :key="description.header">
          <v-card :key="description.header" class="white--text" style="margin-bottom: 10px">
            <v-container fluid grid-list-lg>
              <v-layout column>
                  <div class="headline" style="margin-bottom: 10px">{{ description.header }}</div>
                  <div v-for="item in description.items" :key="item.icon">
                     <v-layout row>
                        <v-flex xs1>{{ item.icon }}</v-flex>
                        <v-flex xs11><span v-html="item.text"></span></v-flex>
                     </v-layout>
                  </div>
              </v-layout>
            </v-container>
          </v-card>
        </template>
      </v-flex>

      <v-flex xs7>
        <v-slide-y-transition mode="out-in">
          <v-layout column align-center>
            <v-data-table
              :headers="headers"
              :items="items"
              :loading="loading"
              :pagination.sync="pagination"
              hide-actions
              class="elevation-1"
            >
              <template slot="items" slot-scope="props">
                <td class="text-xs-left">{{ props.item.rank }}</td>
                <td><span v-bind:class="{ 'you': props.item.is_owner }">{{ props.item.name }}</span></td>
                <td class="text-xs-right">{{ props.item.ratio }}</td>
                <td class="text-xs-right">
                  <v-tooltip right>
                    <span dark color="primary" slot="activator" v-on:click="clickedWallet=props.item.address; walletDialog=true">
                      {{ props.item.address.substring(0, 5) }}
                    </span>
                    <span>{{ props.item.address }}</span>
                  </v-tooltip>
                </td>
                <td class="text-xs-right">{{ props.item.coin }}</td>
              </template>
            </v-data-table>
          </v-layout>
        </v-slide-y-transition>
      </v-flex>

      <v-flex xs2>
        <v-card class="white--text">
            <v-container fluid grid-list-lg>
              <v-layout row>
                <v-flex xs12>
                  <div>
                    <div class="headline">Shop</div>
                    <div>
                      <v-list>
                        <template v-for="item in badges" :key="item.icon">
                          <v-list-tile avatar :key="item.name" @click="">
                            <v-list-tile-avatar>
                              <span class="display-1">{{ item.icon }}</span>
                            </v-list-tile-avatar>
                            <v-list-tile-content>
                              <v-list-tile-title v-html="item.name"></v-list-tile-title>
                              <v-list-tile-sub-title v-html="item.description"></v-list-tile-sub-title>
                            </v-list-tile-content>
                          </v-list-tile>
                        </template>
                      </v-list>
                    </div>
                  </div>
                </v-flex>
              </v-layout>
            </v-container>
        </v-card>
      </v-flex>

      <v-dialog v-model="walletDialog" max-width="500px">
        <v-card>
          <v-card-title>
            <span>{{ clickedWallet }}</span>
          </v-card-title>
          <v-card-actions>
            <v-btn color="primary" flat @click.stop="walletDialog=false">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-layout>
  </v-container>
</template>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h1,
h2 {
  font-weight: normal;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}
a {
  color: #42b983;
}
</style>

<style>
.mist {
  color: #00FF00;
  font-weight: bold;
}
.you {
  color: yellow;
  font-weight: bold;
}
</style>

<script>
/* eslint-disable*/
import axios from "axios";

export default {
  data() {
    return {
      pagination: {
        sortBy: 'ratio',
        descending: true,
        rowsPerPage: -1
      },
      loading: false,
      headers: [
        { text: "Rank", value: "rank" },
        {
          text: "Name",
          align: "left",
          value: "name"
        },
        { text: "Ratio", value: "ratio" },
        { text: "Wallet", value: "address" },
        { text: "Coins", value: "coin" },
      ],
      items: [],
      badges: [
        {
          icon: '😼',
          name: 'Sly',
          description: '2.50PC'
        },
        {
          icon: '🙇',
          name: 'Respect bro',
          description: '1.75PC'
        },
        {
          icon: '😁',
          name: 'Smile',
          description: '1.50PC',
        },
        {
          icon: '🙆',
          name: 'YMCA',
          description: '1.40PC'
        },
      ],
      descriptions: [
        {
          header: '🤔 Why?',
          items: [
            {
              icon: '☯️',
              text: 'We want to promote fairer code reviewing and knowledge sharing.'
            },
          ]
        },
        {
          header: '🎲 How To Play?',
          items: [
            {
              icon: '💹',
              text: 'Your ratio is (# PRs reviewed) / (# PRs you have made)'
            },
            {
              icon: '💻',
              text: 'Inspired by the BitTorrent protocol, in order to increase the health of the reviewing network we should give back more than we take.'
            },
            {
              icon: '🤑',
              text: 'As an incentive you earn Picnic Coin for every hour you have a ratio above 1.0, which can be spent on awesome badges and other goodies in the near future.'
            },
            {
              icon: '🎭',
              text: 'To avoid shaming, we anonymise the names of players with a ratio below 1.0. You can reveal your position by signing in with your Github account.'
            },
          ]
        },
        {
          header: '🤫 Tips',
          items: [
            {
              icon: '💖',
              text: 'Backend developers can earn coins and help find great new colleagues by submitting reviews to the <strong>PicnicSupermarket/backend-interview-submissions</strong> repository!'
            },
          ]
        },
        {
          header: '🏦 Manage your money',
          items: [
            {
              icon: '💬',
              text: 'Message the admin to set a password for your wallet'
            },
            {
              icon: '💸',
              text: 'Download <a href="https://github.com/ethereum/mist/releases" target="_blank">Mist Wallet</a> and run with: <br />' +
                    '<span class="mist">$ mist --rpc http://localhost:8545</span>'
            },
            {
              icon: '💶',
              text: 'Send and spend your hard earned Picnic Coin!'
            },
          ]
        },
      ],
      clickedWallet: '',
      walletDialog: false,
    };
  },
  methods: {
    getAccessToken: function() {
      const token = document.cookie.split(';').filter(item => item.indexOf('X-Access-Token=') >= 0).map(cookie => cookie.substring('X-Access-Token='.length));
      return token[0];
    },
    getRatios: function() {
      this.loading = true;
      const token = this.getAccessToken();
      let headers = {};
      if (token) {
        headers = { 'X-Access-Token': token }
      }
      axios
        .get("https://localhost:9999/api/metrics", { headers: headers })
        .then(response => {
          this.loading = false;
          this.items = response.data.map((item, index) => {
            item["rank"] = index + 1;
            return item;
          });
        })
        .catch(() => {
          this.loading = false;
        });
    },
  },
  mounted () {
    this.getRatios();
    this.leaderboardPoll = setInterval(this.getRatios, 30000);
  },
  beforeDestroy () {
    this.leaderboardPoll && clearInterval(this.leaderboardPoll);
  },
  computed: {
    layout_direction () {
      const layout_direction = {};

      if (this.$vuetify.breakpoint.mdAndDown) {
        layout_direction.column = true;
      }

      return layout_direction
    }
  }
};
</script>
