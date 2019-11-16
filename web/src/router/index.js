import Vue from 'vue'
import Router from 'vue-router'
import PrRatioTable from '@/components/PrRatioTable'

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/',
      name: 'PR Ratio',
      component: PrRatioTable
    }
  ]
})
